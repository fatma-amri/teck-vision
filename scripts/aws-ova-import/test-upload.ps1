param(
    [Parameter(Mandatory = $true)]
    [string]$OvaPath,
    [string]$Region = "eu-west-3",
    [string]$BucketName = "ctf-tekup",
    [string]$BucketPrefix = "ctf_ovas/"
)

$ErrorActionPreference = "Stop"

$FileName = Split-Path -Leaf $OvaPath
$S3Uri = "s3://$BucketName/$BucketPrefix$FileName"

aws s3 cp $OvaPath $S3Uri --region $Region

Write-Host "Uploaded $OvaPath to $S3Uri"
Write-Host "Check Lambda logs and DynamoDB for import status."
