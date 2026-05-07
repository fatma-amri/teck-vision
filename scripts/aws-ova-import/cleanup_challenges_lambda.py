import json
import os
import time
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError


ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ.get("SESSION_TABLE_NAME", "CTFChallenges")
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    now = int(time.time())
    print(f"Running cleanup at {now}")

    processed = 0
    terminated = 0
    expiring = 0

    for item in _scan_sessions():
        processed += 1
        status = item.get("Status")
        expires_at = int(item.get("ExpiresAt", 0) or 0)
        instance_id = item.get("InstanceID")

        if status == "RUNNING" and expires_at and expires_at <= now:
            expiring += 1
            _terminate_expired_session(item, now)
            continue

        if status == "TERMINATING":
            if _is_instance_terminated(instance_id):
                terminated += 1
                _mark_session_terminated(item, now)

    body = {
        "processed": processed,
        "expiring": expiring,
        "terminated": terminated,
    }
    print("Cleanup complete:", json.dumps(body))
    return {"statusCode": 200, "body": json.dumps(body)}


def _scan_sessions():
    scan_kwargs = {}

    while True:
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            yield item

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break

        scan_kwargs["ExclusiveStartKey"] = last_key


def _terminate_expired_session(item, now):
    instance_id = item.get("InstanceID")
    challenge_id = item.get("ChallengeID")
    user_id = item.get("UserID")

    if instance_id:
        print(f"Terminating expired instance {instance_id}")
        try:
            ec2.terminate_instances(InstanceIds=[instance_id])
        except ClientError as exc:
            if _is_not_found(exc):
                print(f"Instance {instance_id} no longer exists; marking session terminated")
                _mark_session_terminated(item, now)
                return
            raise

    table.update_item(
        Key={"ChallengeID": challenge_id, "UserID": user_id},
        UpdateExpression="SET #status = :status, UpdatedAt = :updated_at, CleanupReason = :reason",
        ExpressionAttributeNames={"#status": "Status"},
        ExpressionAttributeValues={
            ":status": "TERMINATING",
            ":updated_at": Decimal(now),
            ":reason": "EXPIRED",
        },
    )


def _is_instance_terminated(instance_id):
    if not instance_id:
        return True

    try:
        response = ec2.describe_instances(InstanceIds=[instance_id])
    except ClientError as exc:
        if _is_not_found(exc):
            print(f"Instance {instance_id} not found; treating as terminated")
            return True
        raise

    instances = [
        instance
        for reservation in response.get("Reservations", [])
        for instance in reservation.get("Instances", [])
    ]
    if not instances:
        print(f"Instance {instance_id} not returned by EC2; treating as terminated")
        return True

    state = instances[0].get("State", {}).get("Name")
    print(f"Instance {instance_id} state is {state}")

    if state == "terminated":
        return True

    if state in {"running", "pending", "stopped", "stopping"}:
        print(f"Re-sending terminate for instance {instance_id}")
        ec2.terminate_instances(InstanceIds=[instance_id])

    return False


def _mark_session_terminated(item, now):
    table.update_item(
        Key={"ChallengeID": item.get("ChallengeID"), "UserID": item.get("UserID")},
        UpdateExpression="SET #status = :status, UpdatedAt = :updated_at, TerminatedAt = :terminated_at",
        ExpressionAttributeNames={"#status": "Status"},
        ExpressionAttributeValues={
            ":status": "TERMINATED",
            ":updated_at": Decimal(now),
            ":terminated_at": Decimal(now),
        },
    )


def _is_not_found(exc):
    code = exc.response.get("Error", {}).get("Code", "")
    return code in {"InvalidInstanceID.NotFound", "InvalidInstanceID.Malformed"}
