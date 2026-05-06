# OVA to AMI Lambda Importer

This folder contains an AWS CLI deployment for a Lambda function that reacts to `.ova` uploads in S3, starts an EC2 VM Import task, and writes import metadata to DynamoDB.

## What It Creates

- S3 bucket: `ctf-tekup`
- S3 upload prefix: `ctf_ovas/`
- DynamoDB table: `ctf-ova-imports`
- Lambda function: `ctf-ova-importer`
- Lambda execution role with S3, EC2 import, DynamoDB, and CloudWatch Logs permissions
- VM Import service role named `vmimport`
- S3 event notification for `ctf_ovas/*.ova`
- EventBridge rule that invokes the Lambda every 5 minutes to update pending imports with the final AMI ID

## Deploy

Run from the repository root:

```powershell
.\scripts\aws-ova-import\deploy.ps1
```

Override defaults if needed:

```powershell
.\scripts\aws-ova-import\deploy.ps1 `
  -Region eu-west-3 `
  -BucketName ctf-tekup `
  -BucketPrefix ctf_ovas/ `
  -TableName ctf-ova-imports
```

The original `aws s3 mb s3://ctf-tekup/ctf_ovas/` shape mixes a bucket and a prefix. S3 buckets do not contain slashes, so the deployment creates the bucket `ctf-tekup` and configures the upload prefix `ctf_ovas/`.

## Test

```powershell
.\scripts\aws-ova-import\test-upload.ps1 -OvaPath C:\path\to\sample.ova
```

Then inspect:

```powershell
aws dynamodb scan --table-name ctf-ova-imports --region eu-west-3
aws logs tail /aws/lambda/ctf-ova-importer --follow --region eu-west-3
```

## DynamoDB Items

Each upload creates an item like:

```json
{
  "challenge_id": "redis0001",
  "nbr": 1,
  "ami_id": "ami-...",
  "import_task_id": "import-ami-...",
  "import_status": "completed",
  "s3_bucket": "ctf-tekup",
  "s3_key": "ctf_ovas/sample.ova"
}
```

VM Import is asynchronous. The initial S3-triggered Lambda invocation stores the import task immediately. The scheduled reconciliation invocation updates `ami_id` once EC2 reports the import as completed.
