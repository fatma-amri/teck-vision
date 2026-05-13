# Educate VPC + API/Lambda Starter

This module provisions an isolated AWS network and an API endpoint that starts EC2 instances for the **educate** section.

## What It Creates

- VPC: `10.0.0.0/16`
- Public subnet: `10.0.1.0/24`
- Private subnet: `10.0.2.0/24`
- Internet Gateway + public route table (`0.0.0.0/0 -> IGW`)
- Private route table:
  - Isolated by default
  - Optional NAT route when `-EnableNat` is set
- Security groups:
  - Public SG (for optional public-facing instances)
  - Private SG (for private educate instances)
- Lambda function to start EC2 instances in the private subnet
- Lambda function to stop/terminate user educate instances
- HTTP API Gateway endpoints for start/stop
- IAM role/policy for Lambda
- DynamoDB table to track educate sessions (`ChallengeID` + `UserID`)

## Deploy

Run from repo root:

```powershell
.\scripts\aws-educate\deploy.ps1 `
  -Region eu-west-3 `
  -AmiId ami-xxxxxxxxxxxxxxxxx
```

### Optional parameters

- `-EnableNat`: create NAT Gateway in public subnet and route private subnet internet egress through NAT.
- `-InstanceType`: default `t3.micro`
- `-VpcName`: default `teck-vision-educate-vpc`
- `-StartFunctionName`: default `teck-vision-educate-start-instance`
- `-StopFunctionName`: default `teck-vision-educate-stop-instance`
- `-ApiName`: default `teck-vision-educate-api`
- `-SessionTableName`: default `EducateChallenges`
- `-Ec2InstanceProfileArn`: optional instance profile ARN if your started EC2 instances need IAM permissions.

Example with NAT:

```powershell
.\scripts\aws-educate\deploy.ps1 `
  -Region eu-west-3 `
  -AmiId ami-xxxxxxxxxxxxxxxxx `
  -EnableNat
```

## Test the API

After deployment, use the printed endpoint:

```powershell
$body = @{ user_id = "123"; challenge_id = "educate-linux-01"; ami_id = "ami-xxxxxxxxxxxxxxxxx" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://<api-id>.execute-api.<region>.amazonaws.com/start" -ContentType "application/json" -Body $body
```

Start response includes:

- `instance_id`
- `state`
- `challenge_id`
- `private_ip` (when available)

Stop request:

```powershell
$body = @{ user_id = "123"; challenge_id = "educate-linux-01" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://<api-id>.execute-api.<region>.amazonaws.com/stop" -ContentType "application/json" -Body $body
```

