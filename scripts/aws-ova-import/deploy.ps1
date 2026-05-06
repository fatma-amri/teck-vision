param(
    [string]$Region = "eu-west-3",
    [string]$BucketName = "ctf-tekup",
    [string]$BucketPrefix = "ctf_ovas/",
    [string]$TableName = "ctf-ova-imports",
    [string]$FunctionName = "ctf-ova-importer",
    [string]$LambdaRoleName = "ctf-ova-importer-lambda-role",
    [string]$VmImportRoleName = "vmimport",
    [string]$ChallengePrefix = "redis",
    [string]$ScheduleName = "ctf-ova-importer-reconcile",
    [switch]$SkipSchedule
)

$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BuildDir = Join-Path $ScriptDir "build"
$PackagePath = Join-Path $BuildDir "lambda.zip"

New-Item -ItemType Directory -Path $BuildDir -Force | Out-Null

function Write-JsonFile {
    param([string]$Path, [object]$Object)
    $Object | ConvertTo-Json -Depth 20 | Set-Content -Path $Path -Encoding UTF8
}

function Get-AccountId {
    aws sts get-caller-identity --query Account --output text
}

function Invoke-OptionalAws {
    param([scriptblock]$Command)

    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Command 2>$null | Out-Null
        return $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }
}

function Ensure-Bucket {
    $ExitCode = Invoke-OptionalAws { aws s3api head-bucket --bucket $BucketName }
    if ($ExitCode -ne 0) {
        aws s3api create-bucket `
            --bucket $BucketName `
            --region $Region `
            --create-bucket-configuration LocationConstraint=$Region | Out-Null
    }
}

function Ensure-Table {
    $ExitCode = Invoke-OptionalAws { aws dynamodb describe-table --table-name $TableName --region $Region }
    if ($ExitCode -ne 0) {
        aws dynamodb create-table `
            --table-name $TableName `
            --attribute-definitions AttributeName=challenge_id,AttributeType=S `
            --key-schema AttributeName=challenge_id,KeyType=HASH `
            --billing-mode PAY_PER_REQUEST `
            --region $Region | Out-Null

        aws dynamodb wait table-exists --table-name $TableName --region $Region
    }
}

function Ensure-VmImportRole {
    $TrustPath = Join-Path $BuildDir "vmimport-trust-policy.json"
    $PolicyPath = Join-Path $BuildDir "vmimport-role-policy.json"

    Write-JsonFile $TrustPath @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{ Service = "vmie.amazonaws.com" }
                Action = "sts:AssumeRole"
                Condition = @{
                    StringEquals = @{ "sts:Externalid" = "vmimport" }
                }
            }
        )
    }

    $ExitCode = Invoke-OptionalAws { aws iam get-role --role-name $VmImportRoleName }
    if ($ExitCode -ne 0) {
        aws iam create-role `
            --role-name $VmImportRoleName `
            --assume-role-policy-document "file://$TrustPath" | Out-Null
    }

    Write-JsonFile $PolicyPath @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = @("s3:GetBucketLocation", "s3:GetObject", "s3:ListBucket")
                Resource = @(
                    "arn:aws:s3:::$BucketName",
                    "arn:aws:s3:::$BucketName/$BucketPrefix*"
                )
            },
            @{
                Effect = "Allow"
                Action = @(
                    "ec2:ModifySnapshotAttribute",
                    "ec2:CopySnapshot",
                    "ec2:RegisterImage",
                    "ec2:Describe*"
                )
                Resource = "*"
            }
        )
    }

    aws iam put-role-policy `
        --role-name $VmImportRoleName `
        --policy-name "$VmImportRoleName-policy" `
        --policy-document "file://$PolicyPath" | Out-Null
}

function Ensure-LambdaRole {
    param([string]$AccountId)

    $TrustPath = Join-Path $BuildDir "lambda-trust-policy.json"
    $PolicyPath = Join-Path $BuildDir "lambda-permissions-policy.json"

    Write-JsonFile $TrustPath @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{ Service = "lambda.amazonaws.com" }
                Action = "sts:AssumeRole"
            }
        )
    }

    $ExitCode = Invoke-OptionalAws { aws iam get-role --role-name $LambdaRoleName }
    if ($ExitCode -ne 0) {
        aws iam create-role `
            --role-name $LambdaRoleName `
            --assume-role-policy-document "file://$TrustPath" | Out-Null
    }

    aws iam attach-role-policy `
        --role-name $LambdaRoleName `
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" | Out-Null

    Write-JsonFile $PolicyPath @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Action = @("s3:GetObject", "s3:GetObjectVersion", "s3:ListBucket")
                Resource = @(
                    "arn:aws:s3:::$BucketName",
                    "arn:aws:s3:::$BucketName/$BucketPrefix*"
                )
            },
            @{
                Effect = "Allow"
                Action = @("ec2:ImportImage", "ec2:DescribeImportImageTasks", "ec2:CreateTags")
                Resource = "*"
            },
            @{
                Effect = "Allow"
                Action = "iam:PassRole"
                Resource = "arn:aws:iam::$AccountId`:role/$VmImportRoleName"
            },
            @{
                Effect = "Allow"
                Action = @("dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Scan", "dynamodb:GetItem")
                Resource = "arn:aws:dynamodb:$Region`:$AccountId`:table/$TableName"
            }
        )
    }

    aws iam put-role-policy `
        --role-name $LambdaRoleName `
        --policy-name "$LambdaRoleName-policy" `
        --policy-document "file://$PolicyPath" | Out-Null

    $RoleArn = aws iam get-role --role-name $LambdaRoleName --query Role.Arn --output text
    Start-Sleep -Seconds 10
    return $RoleArn
}

function Build-Package {
    if (Test-Path $PackagePath) {
        Remove-Item -Path $PackagePath -Force
    }

    Compress-Archive `
        -Path (Join-Path $ScriptDir "lambda_function.py") `
        -DestinationPath $PackagePath `
        -Force
}

function Ensure-Lambda {
    param([string]$RoleArn)

    $EnvVars = "Variables={TABLE_NAME=$TableName,CHALLENGE_PREFIX=$ChallengePrefix}"

    $ExitCode = Invoke-OptionalAws { aws lambda get-function --function-name $FunctionName --region $Region }
    if ($ExitCode -ne 0) {
        aws lambda create-function `
            --function-name $FunctionName `
            --runtime python3.12 `
            --handler lambda_function.lambda_handler `
            --role $RoleArn `
            --zip-file "fileb://$PackagePath" `
            --timeout 60 `
            --memory-size 256 `
            --environment $EnvVars `
            --region $Region | Out-Null
    }
    else {
        aws lambda update-function-code `
            --function-name $FunctionName `
            --zip-file "fileb://$PackagePath" `
            --region $Region | Out-Null

        aws lambda wait function-updated --function-name $FunctionName --region $Region

        aws lambda update-function-configuration `
            --function-name $FunctionName `
            --runtime python3.12 `
            --handler lambda_function.lambda_handler `
            --role $RoleArn `
            --timeout 60 `
            --memory-size 256 `
            --environment $EnvVars `
            --region $Region | Out-Null
    }

    aws lambda wait function-active --function-name $FunctionName --region $Region
    return aws lambda get-function --function-name $FunctionName --query Configuration.FunctionArn --output text --region $Region
}

function Configure-S3Notification {
    param([string]$FunctionArn, [string]$AccountId)

    aws lambda add-permission `
        --function-name $FunctionName `
        --statement-id "AllowS3Invoke-$BucketName" `
        --action lambda:InvokeFunction `
        --principal s3.amazonaws.com `
        --source-arn "arn:aws:s3:::$BucketName" `
        --source-account $AccountId `
        --region $Region 2>$null | Out-Null

    $NotificationPath = Join-Path $BuildDir "s3-notification.json"
    Write-JsonFile $NotificationPath @{
        LambdaFunctionConfigurations = @(
            @{
                Id = "InvokeOvaImporter"
                LambdaFunctionArn = $FunctionArn
                Events = @("s3:ObjectCreated:*")
                Filter = @{
                    Key = @{
                        FilterRules = @(
                            @{ Name = "prefix"; Value = $BucketPrefix },
                            @{ Name = "suffix"; Value = ".ova" }
                        )
                    }
                }
            }
        )
    }

    aws s3api put-bucket-notification-configuration `
        --bucket $BucketName `
        --notification-configuration "file://$NotificationPath" `
        --region $Region | Out-Null
}

function Configure-Schedule {
    param([string]$FunctionArn)

    if ($SkipSchedule) {
        return
    }

    aws events put-rule `
        --name $ScheduleName `
        --schedule-expression "rate(5 minutes)" `
        --state ENABLED `
        --region $Region | Out-Null

    aws lambda add-permission `
        --function-name $FunctionName `
        --statement-id "AllowEventBridgeInvoke-$ScheduleName" `
        --action lambda:InvokeFunction `
        --principal events.amazonaws.com `
        --source-arn "arn:aws:events:$Region`:$(Get-AccountId):rule/$ScheduleName" `
        --region $Region 2>$null | Out-Null

    $TargetsPath = Join-Path $BuildDir "eventbridge-targets.json"
    Write-JsonFile $TargetsPath @(
        @{
            Id = "OvaImportReconcileLambda"
            Arn = $FunctionArn
            Input = '{"source":"eventbridge.reconcile"}'
        }
    )

    aws events put-targets `
        --rule $ScheduleName `
        --targets "file://$TargetsPath" `
        --region $Region | Out-Null
}

$AccountId = Get-AccountId

Ensure-Bucket
Ensure-Table
Ensure-VmImportRole
$LambdaRoleArn = Ensure-LambdaRole -AccountId $AccountId
Build-Package
$FunctionArn = Ensure-Lambda -RoleArn $LambdaRoleArn
Configure-S3Notification -FunctionArn $FunctionArn -AccountId $AccountId
Configure-Schedule -FunctionArn $FunctionArn

Write-Host "Deployment complete."
Write-Host "Upload OVA files to: s3://$BucketName/$BucketPrefix"
Write-Host "Lambda function: $FunctionArn"
Write-Host "DynamoDB table: $TableName"
