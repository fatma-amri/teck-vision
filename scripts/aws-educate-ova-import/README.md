# Educate OVA to AMI Importer

Dedicated OVA importer for the **Educate** section, isolated from the Rooms/CTF importer.

## Creates

- S3 bucket for Educate OVA uploads (default: `ctf-tekup-educate`)
- S3 prefix for OVA objects (default: `educate_ovas/`)
- DynamoDB table (default: `ctf-educate-ova-imports`)
- Importer Lambda (default: `ctf-educate-ova-importer`)
- EventBridge reconciliation rule (every 5 minutes)
- S3 -> Lambda notification for `*.ova` uploads

## Deploy

```powershell
.\scripts\aws-educate-ova-import\deploy.ps1 -Region eu-west-3
```

Optional overrides:

```powershell
.\scripts\aws-educate-ova-import\deploy.ps1 `
  -Region eu-west-3 `
  -BucketName ctf-tekup-educate `
  -BucketPrefix educate_ovas/ `
  -TableName ctf-educate-ova-imports `
  -ChallengePrefix edu
```

## App config to use in Educate admin

- `EDUCATE_OVA_S3_BUCKET`
- `EDUCATE_OVA_S3_PREFIX`
- `EDUCATE_OVA_S3_REGION`
- `EDUCATE_OVA_IMPORTS_TABLE`

If unset, code defaults to:

- Bucket: `ctf-tekup-educate`
- Prefix: `educate_ovas`
- Region: `eu-west-3`
- Table: `ctf-educate-ova-imports`

