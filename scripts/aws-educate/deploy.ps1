param(
    [string]$AmiId = "",
    [string]$Region = "eu-west-3",
    [string]$VpcName = "teck-vision-educate-vpc",
    [string]$PublicSubnetCidr = "10.0.1.0/24",
    [string]$PrivateSubnetCidr = "10.0.2.0/24",
    [string]$VpcCidr = "10.0.0.0/16",
    [string]$FunctionName = "teck-vision-educate-start-instance",
    [string]$LambdaRoleName = "teck-vision-educate-lambda-role",
    [string]$ApiName = "teck-vision-educate-api",
    [string]$InstanceType = "t3.micro",
    [string]$KeyName = "",
    [string]$Ec2InstanceProfileArn = "",
    [switch]$EnableNat
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
    $Object | ConvertTo-Json -Depth 20 | Set-Content -Path $Path -Encoding Ascii
}

function Invoke-OptionalAws {
    param([scriptblock]$Command)
    $Prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Command 2>$null | Out-Null
        return $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $Prev
    }
}

function Ensure-Vpc {
    $Existing = aws ec2 describe-vpcs `
        --region $Region `
        --filters "Name=tag:Name,Values=$VpcName" `
        --query "Vpcs[0].VpcId" `
        --output text

    if ($Existing -and $Existing -ne "None") {
        return $Existing
    }

    $VpcId = aws ec2 create-vpc `
        --region $Region `
        --cidr-block $VpcCidr `
        --query "Vpc.VpcId" `
        --output text

    aws ec2 modify-vpc-attribute --region $Region --vpc-id $VpcId --enable-dns-support '{"Value":true}' | Out-Null
    aws ec2 modify-vpc-attribute --region $Region --vpc-id $VpcId --enable-dns-hostnames '{"Value":true}' | Out-Null
    aws ec2 create-tags --region $Region --resources $VpcId --tags "Key=Name,Value=$VpcName" | Out-Null
    return $VpcId
}

function Ensure-Subnets {
    param([string]$VpcId)

    $Az = aws ec2 describe-availability-zones --region $Region --query "AvailabilityZones[0].ZoneName" --output text

    $PublicSubnetId = aws ec2 describe-subnets `
        --region $Region `
        --filters "Name=vpc-id,Values=$VpcId" "Name=cidr-block,Values=$PublicSubnetCidr" `
        --query "Subnets[0].SubnetId" `
        --output text

    if (-not $PublicSubnetId -or $PublicSubnetId -eq "None") {
        $PublicSubnetId = aws ec2 create-subnet `
            --region $Region `
            --vpc-id $VpcId `
            --cidr-block $PublicSubnetCidr `
            --availability-zone $Az `
            --query "Subnet.SubnetId" `
            --output text
        aws ec2 create-tags --region $Region --resources $PublicSubnetId --tags "Key=Name,Value=$VpcName-public-subnet" | Out-Null
    }
    aws ec2 modify-subnet-attribute --region $Region --subnet-id $PublicSubnetId --map-public-ip-on-launch | Out-Null

    $PrivateSubnetId = aws ec2 describe-subnets `
        --region $Region `
        --filters "Name=vpc-id,Values=$VpcId" "Name=cidr-block,Values=$PrivateSubnetCidr" `
        --query "Subnets[0].SubnetId" `
        --output text
    if (-not $PrivateSubnetId -or $PrivateSubnetId -eq "None") {
        $PrivateSubnetId = aws ec2 create-subnet `
            --region $Region `
            --vpc-id $VpcId `
            --cidr-block $PrivateSubnetCidr `
            --availability-zone $Az `
            --query "Subnet.SubnetId" `
            --output text
        aws ec2 create-tags --region $Region --resources $PrivateSubnetId --tags "Key=Name,Value=$VpcName-private-subnet" | Out-Null
    }

    return @{ PublicSubnetId = $PublicSubnetId; PrivateSubnetId = $PrivateSubnetId }
}

function Ensure-IgwAndRoutes {
    param([string]$VpcId, [string]$PublicSubnetId, [string]$PrivateSubnetId)

    $IgwId = aws ec2 describe-internet-gateways `
        --region $Region `
        --filters "Name=attachment.vpc-id,Values=$VpcId" `
        --query "InternetGateways[0].InternetGatewayId" `
        --output text
    if (-not $IgwId -or $IgwId -eq "None") {
        $IgwId = aws ec2 create-internet-gateway --region $Region --query "InternetGateway.InternetGatewayId" --output text
        aws ec2 attach-internet-gateway --region $Region --internet-gateway-id $IgwId --vpc-id $VpcId | Out-Null
        aws ec2 create-tags --region $Region --resources $IgwId --tags "Key=Name,Value=$VpcName-igw" | Out-Null
    }

    $PublicRtId = aws ec2 describe-route-tables `
        --region $Region `
        --filters "Name=vpc-id,Values=$VpcId" "Name=tag:Name,Values=$VpcName-public-rt" `
        --query "RouteTables[0].RouteTableId" `
        --output text
    if (-not $PublicRtId -or $PublicRtId -eq "None") {
        $PublicRtId = aws ec2 create-route-table --region $Region --vpc-id $VpcId --query "RouteTable.RouteTableId" --output text
        aws ec2 create-tags --region $Region --resources $PublicRtId --tags "Key=Name,Value=$VpcName-public-rt" | Out-Null
    }
    Invoke-OptionalAws { aws ec2 create-route --region $Region --route-table-id $PublicRtId --destination-cidr-block "0.0.0.0/0" --gateway-id $IgwId } | Out-Null
    Invoke-OptionalAws { aws ec2 associate-route-table --region $Region --route-table-id $PublicRtId --subnet-id $PublicSubnetId } | Out-Null

    $PrivateRtId = aws ec2 describe-route-tables `
        --region $Region `
        --filters "Name=vpc-id,Values=$VpcId" "Name=tag:Name,Values=$VpcName-private-rt" `
        --query "RouteTables[0].RouteTableId" `
        --output text
    if (-not $PrivateRtId -or $PrivateRtId -eq "None") {
        $PrivateRtId = aws ec2 create-route-table --region $Region --vpc-id $VpcId --query "RouteTable.RouteTableId" --output text
        aws ec2 create-tags --region $Region --resources $PrivateRtId --tags "Key=Name,Value=$VpcName-private-rt" | Out-Null
    }
    Invoke-OptionalAws { aws ec2 associate-route-table --region $Region --route-table-id $PrivateRtId --subnet-id $PrivateSubnetId } | Out-Null

    if ($EnableNat) {
        $NatGatewayId = aws ec2 describe-nat-gateways `
            --region $Region `
            --filter "Name=vpc-id,Values=$VpcId" "Name=state,Values=available,pending" `
            --query "NatGateways[0].NatGatewayId" `
            --output text

        if (-not $NatGatewayId -or $NatGatewayId -eq "None") {
            $AllocationId = aws ec2 allocate-address --region $Region --domain vpc --query "AllocationId" --output text
            $NatGatewayId = aws ec2 create-nat-gateway `
                --region $Region `
                --subnet-id $PublicSubnetId `
                --allocation-id $AllocationId `
                --query "NatGateway.NatGatewayId" `
                --output text
            aws ec2 create-tags --region $Region --resources $NatGatewayId --tags "Key=Name,Value=$VpcName-nat" | Out-Null
            aws ec2 wait nat-gateway-available --region $Region --nat-gateway-ids $NatGatewayId
        }

        Invoke-OptionalAws { aws ec2 create-route --region $Region --route-table-id $PrivateRtId --destination-cidr-block "0.0.0.0/0" --nat-gateway-id $NatGatewayId } | Out-Null
    }

    return @{ IgwId = $IgwId; PublicRtId = $PublicRtId; PrivateRtId = $PrivateRtId }
}

function Ensure-SecurityGroups {
    param([string]$VpcId, [string]$PublicSubnetCidr)

    $PublicSgId = aws ec2 describe-security-groups `
        --region $Region `
        --filters "Name=vpc-id,Values=$VpcId" "Name=group-name,Values=$VpcName-public-sg" `
        --query "SecurityGroups[0].GroupId" `
        --output text
    if (-not $PublicSgId -or $PublicSgId -eq "None") {
        $PublicSgId = aws ec2 create-security-group `
            --region $Region `
            --vpc-id $VpcId `
            --group-name "$VpcName-public-sg" `
            --description "Public subnet SG for educate VPC" `
            --query "GroupId" `
            --output text
        $PublicIngress = @(
            @{
                IpProtocol = "tcp"
                FromPort = 22
                ToPort = 22
                IpRanges = @(
                    @{
                        CidrIp = "0.0.0.0/0"
                        Description = "SSH"
                    }
                )
            }
        ) | ConvertTo-Json -Depth 10 -Compress
        aws ec2 authorize-security-group-ingress --region $Region --group-id $PublicSgId --ip-permissions $PublicIngress | Out-Null
    }

    $PrivateSgId = aws ec2 describe-security-groups `
        --region $Region `
        --filters "Name=vpc-id,Values=$VpcId" "Name=group-name,Values=$VpcName-private-sg" `
        --query "SecurityGroups[0].GroupId" `
        --output text
    if (-not $PrivateSgId -or $PrivateSgId -eq "None") {
        $PrivateSgId = aws ec2 create-security-group `
            --region $Region `
            --vpc-id $VpcId `
            --group-name "$VpcName-private-sg" `
            --description "Private subnet SG for educate VMs" `
            --query "GroupId" `
            --output text

        # Allow traffic from public subnet to private instances (adjust ports later as needed).
        $PrivateIngress = @(
            @{
                IpProtocol = "-1"
                IpRanges = @(
                    @{
                        CidrIp = $PublicSubnetCidr
                        Description = "From public subnet"
                    }
                )
            }
        ) | ConvertTo-Json -Depth 10 -Compress
        aws ec2 authorize-security-group-ingress `
            --region $Region `
            --group-id $PrivateSgId `
            --ip-permissions $PrivateIngress | Out-Null
    }

    return @{ PublicSgId = $PublicSgId; PrivateSgId = $PrivateSgId }
}

function Ensure-LambdaRole {
    $AccountId = aws sts get-caller-identity --query Account --output text
    $TrustPath = Join-Path $BuildDir "educate-lambda-trust.json"
    $PolicyPath = Join-Path $BuildDir "educate-lambda-policy.json"

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
        aws iam create-role --role-name $LambdaRoleName --assume-role-policy-document "file://$TrustPath" | Out-Null
    }

    aws iam attach-role-policy `
        --role-name $LambdaRoleName `
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" | Out-Null

    $Statements = @(
        @{
            Effect = "Allow"
            Action = @("ec2:RunInstances", "ec2:DescribeInstances", "ec2:CreateTags")
            Resource = "*"
        }
    )
    if ($Ec2InstanceProfileArn) {
        $Statements += @{
            Effect = "Allow"
            Action = "iam:PassRole"
            Resource = $Ec2InstanceProfileArn
        }
    }

    Write-JsonFile $PolicyPath @{
        Version = "2012-10-17"
        Statement = $Statements
    }

    aws iam put-role-policy `
        --role-name $LambdaRoleName `
        --policy-name "$LambdaRoleName-inline" `
        --policy-document "file://$PolicyPath" | Out-Null

    Start-Sleep -Seconds 8
    return aws iam get-role --role-name $LambdaRoleName --query Role.Arn --output text
}

function Build-Package {
    if (Test-Path $PackagePath) {
        Remove-Item -Path $PackagePath -Force
    }
    Compress-Archive `
        -Path (Join-Path $ScriptDir "start_educate_instance_lambda.py") `
        -DestinationPath $PackagePath `
        -Force
}

function Ensure-Lambda {
    param(
        [string]$RoleArn,
        [string]$PrivateSubnetId,
        [string]$PrivateSgId
    )

    $EnvObject = @{
        Variables = @{
            AMI_ID = if ($AmiId) { $AmiId } else { "pending" }
            PRIVATE_SUBNET_ID = $PrivateSubnetId
            PRIVATE_SECURITY_GROUP_ID = $PrivateSgId
            INSTANCE_TYPE = $InstanceType
            KEY_NAME = $KeyName
            EC2_INSTANCE_PROFILE_ARN = $Ec2InstanceProfileArn
        }
    }
    $EnvPath = Join-Path $BuildDir "lambda-environment.json"
    Write-JsonFile -Path $EnvPath -Object $EnvObject

    $ExitCode = Invoke-OptionalAws { aws lambda get-function --function-name $FunctionName --region $Region }
    if ($ExitCode -ne 0) {
        aws lambda create-function `
            --function-name $FunctionName `
            --runtime python3.12 `
            --handler start_educate_instance_lambda.lambda_handler `
            --role $RoleArn `
            --zip-file "fileb://$PackagePath" `
            --timeout 90 `
            --memory-size 256 `
            --environment "file://$EnvPath" `
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
            --handler start_educate_instance_lambda.lambda_handler `
            --role $RoleArn `
            --timeout 90 `
            --memory-size 256 `
            --environment "file://$EnvPath" `
            --region $Region | Out-Null
    }

    aws lambda wait function-active --function-name $FunctionName --region $Region
    $FunctionArn = aws lambda get-function --function-name $FunctionName --region $Region --query "Configuration.FunctionArn" --output text
    if (-not $FunctionArn -or $FunctionArn -eq "None") {
        throw "Failed to resolve Lambda function ARN for $FunctionName"
    }
    return $FunctionArn
}

function Ensure-HttpApi {
    param([string]$FunctionArn)

    $ApiId = aws apigatewayv2 get-apis --region $Region --query "Items[?Name=='$ApiName']|[0].ApiId" --output text
    if (-not $ApiId -or $ApiId -eq "None") {
        $ApiId = aws apigatewayv2 create-api `
            --region $Region `
            --name $ApiName `
            --protocol-type HTTP `
            --cors-configuration "AllowOrigins=*,AllowMethods=POST,OPTIONS,AllowHeaders=content-type,authorization" `
            --query "ApiId" `
            --output text
    }

    $IntegrationId = aws apigatewayv2 get-integrations --region $Region --api-id $ApiId --query "Items[0].IntegrationId" --output text
    if (-not $IntegrationId -or $IntegrationId -eq "None") {
        $IntegrationId = aws apigatewayv2 create-integration `
            --region $Region `
            --api-id $ApiId `
            --integration-type AWS_PROXY `
            --integration-uri $FunctionArn `
            --payload-format-version "2.0" `
            --query "IntegrationId" `
            --output text
    }

    $RouteTarget = "integrations/$IntegrationId"
    $ExistingRoute = aws apigatewayv2 get-routes --region $Region --api-id $ApiId --query "Items[?RouteKey=='POST /start']|[0].RouteId" --output text
    if (-not $ExistingRoute -or $ExistingRoute -eq "None") {
        aws apigatewayv2 create-route --region $Region --api-id $ApiId --route-key "POST /start" --target $RouteTarget | Out-Null
    }

    $Stage = aws apigatewayv2 get-stages --region $Region --api-id $ApiId --query "Items[?StageName=='`$default']|[0].StageName" --output text
    if (-not $Stage -or $Stage -eq "None") {
        aws apigatewayv2 create-stage --region $Region --api-id $ApiId --stage-name '$default' --auto-deploy | Out-Null
    }

    $StatementId = "AllowApiInvoke-$ApiId"
    $ExitCode = Invoke-OptionalAws {
        aws lambda add-permission `
            --function-name $FunctionName `
            --statement-id $StatementId `
            --action lambda:InvokeFunction `
            --principal apigateway.amazonaws.com `
            --source-arn "arn:aws:execute-api:$Region`:$(aws sts get-caller-identity --query Account --output text):$ApiId/*/*/start" `
            --region $Region
    }
    $null = $ExitCode

    return "https://$ApiId.execute-api.$Region.amazonaws.com/start"
}

Write-Host "Creating/validating VPC networking..."
$VpcId = Ensure-Vpc
$Subnets = Ensure-Subnets -VpcId $VpcId
$Routes = Ensure-IgwAndRoutes -VpcId $VpcId -PublicSubnetId $Subnets.PublicSubnetId -PrivateSubnetId $Subnets.PrivateSubnetId
$Sgs = Ensure-SecurityGroups -VpcId $VpcId -PublicSubnetCidr $PublicSubnetCidr

Write-Host "Creating/validating Lambda + API Gateway..."
$RoleArn = Ensure-LambdaRole
Build-Package
$FunctionArn = Ensure-Lambda -RoleArn $RoleArn -PrivateSubnetId $Subnets.PrivateSubnetId -PrivateSgId $Sgs.PrivateSgId
$StartEndpoint = Ensure-HttpApi -FunctionArn $FunctionArn

Write-Host ""
Write-Host "Deployment complete."
Write-Host "VPC:                $VpcId"
Write-Host "Public Subnet:      $($Subnets.PublicSubnetId) ($PublicSubnetCidr)"
Write-Host "Private Subnet:     $($Subnets.PrivateSubnetId) ($PrivateSubnetCidr)"
Write-Host "Public SG:          $($Sgs.PublicSgId)"
Write-Host "Private SG:         $($Sgs.PrivateSgId)"
Write-Host "Lambda:             $FunctionArn"
Write-Host "Start endpoint:     $StartEndpoint"
if ($EnableNat) {
    Write-Host "Private route table has NAT egress enabled."
}
else {
    Write-Host "Private subnet is isolated (no internet egress route)."
}
