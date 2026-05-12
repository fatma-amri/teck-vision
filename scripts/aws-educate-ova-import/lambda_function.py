import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import unquote_plus

import boto3


TABLE_NAME = os.environ["TABLE_NAME"]
CHALLENGE_PREFIX = os.environ.get("CHALLENGE_PREFIX", "edu")
COUNTER_KEY = os.environ.get("COUNTER_KEY", "__counter__")
IMPORT_DESCRIPTION_PREFIX = os.environ.get("IMPORT_DESCRIPTION_PREFIX", "Educate OVA import")
PENDING_SCAN_LIMIT = int(os.environ.get("PENDING_SCAN_LIMIT", "25"))

dynamodb = boto3.resource("dynamodb")
ec2 = boto3.client("ec2")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    if _is_s3_event(event):
        return _handle_s3_records(event["Records"])
    return _reconcile_pending_imports()


def _is_s3_event(event):
    return bool(event.get("Records")) and event["Records"][0].get("eventSource") == "aws:s3"


def _handle_s3_records(records):
    results = []
    for record in records:
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])

        if not key.lower().endswith(".ova"):
            results.append({"bucket": bucket, "key": key, "skipped": "not an .ova file"})
            continue

        challenge_id, nbr = _next_challenge_id()
        import_response = _start_import(bucket, key, challenge_id)
        now = _utc_now()

        item = {
            "challenge_id": challenge_id,
            "nbr": Decimal(nbr),
            "ami_id": import_response.get("ImageId", ""),
            "import_task_id": import_response["ImportTaskId"],
            "import_status": import_response.get("Status", "active"),
            "s3_bucket": bucket,
            "s3_key": key,
            "created_at": now,
            "updated_at": now,
        }

        table.put_item(Item=item)
        results.append(_jsonable(item))

    return {"processed": results}


def _next_challenge_id():
    response = table.update_item(
        Key={"challenge_id": COUNTER_KEY},
        UpdateExpression="SET nbr = if_not_exists(nbr, :zero) + :one, updated_at = :updated_at",
        ExpressionAttributeValues={
            ":zero": Decimal(0),
            ":one": Decimal(1),
            ":updated_at": _utc_now(),
        },
        ReturnValues="UPDATED_NEW",
    )
    nbr = int(response["Attributes"]["nbr"])
    return f"{CHALLENGE_PREFIX}{nbr:04d}", nbr


def _start_import(bucket, key, challenge_id):
    return ec2.import_image(
        Description=f"{IMPORT_DESCRIPTION_PREFIX} {challenge_id} from s3://{bucket}/{key}",
        DiskContainers=[
            {
                "Description": f"{challenge_id} OVA",
                "Format": "ova",
                "UserBucket": {"S3Bucket": bucket, "S3Key": key},
            }
        ],
        TagSpecifications=[
            {
                "ResourceType": "import-image-task",
                "Tags": [
                    {"Key": "ChallengeId", "Value": challenge_id},
                    {"Key": "SourceS3Bucket", "Value": bucket},
                    {"Key": "SourceS3Key", "Value": key},
                    {"Key": "Section", "Value": "educate"},
                ],
            }
        ],
    )


def _reconcile_pending_imports():
    response = table.scan(
        FilterExpression="attribute_exists(import_task_id) AND import_status <> :completed",
        ExpressionAttributeValues={":completed": "completed"},
        Limit=PENDING_SCAN_LIMIT,
    )

    updated = []
    for item in response.get("Items", []):
        task_id = item["import_task_id"]
        describe = ec2.describe_import_image_tasks(ImportTaskIds=[task_id])
        tasks = describe.get("ImportImageTasks", [])
        if not tasks:
            continue

        task = tasks[0]
        status = task.get("Status", "unknown")
        ami_id = task.get("ImageId", item.get("ami_id", ""))

        table.update_item(
            Key={"challenge_id": item["challenge_id"]},
            UpdateExpression=(
                "SET import_status = :status, ami_id = :ami_id, "
                "status_message = :message, updated_at = :updated_at"
            ),
            ExpressionAttributeValues={
                ":status": status,
                ":ami_id": ami_id,
                ":message": task.get("StatusMessage", ""),
                ":updated_at": _utc_now(),
            },
        )
        updated.append(
            {
                "challenge_id": item["challenge_id"],
                "import_task_id": task_id,
                "import_status": status,
                "ami_id": ami_id,
            }
        )

    return {"updated": updated, "scanned": len(response.get("Items", []))}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value):
    return json.loads(json.dumps(value, default=_json_default))


def _json_default(value):
    if isinstance(value, Decimal):
        return int(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

