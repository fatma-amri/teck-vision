import json
import os
import time

import boto3


ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")

SESSION_TABLE_NAME = os.environ.get("SESSION_TABLE_NAME", "CTFChallenges")
session_table = dynamodb.Table(SESSION_TABLE_NAME)


def lambda_handler(event, context):
    try:
        print("EVENT:", json.dumps(event))
        body = _parse_body(event)

        challenge_id = str(body.get("challenge_id", "")).strip()
        user_id = _get_user_id(event, body)

        if not challenge_id:
            return response(400, {"error": "Missing challenge_id"})
        if not user_id:
            return response(401, {"error": "Missing authenticated user_id"})

        existing = session_table.get_item(
            Key={"ChallengeID": challenge_id, "UserID": user_id}
        )
        item = existing.get("Item")
        if not item:
            return response(404, {"error": "No running instance found"})

        instance_id = item.get("InstanceID")
        if not instance_id:
            return response(400, {"error": "No instance linked to this session"})

        current_status = item.get("Status")
        if current_status in {"STOPPED", "TERMINATED", "TERMINATING"}:
            return response(
                200,
                {
                    "message": "Instance is already stopped",
                    "instance_id": instance_id,
                    "status": current_status,
                },
            )

        ec2.terminate_instances(InstanceIds=[instance_id])
        stopped_at = int(time.time())

        session_table.update_item(
            Key={"ChallengeID": challenge_id, "UserID": user_id},
            UpdateExpression="SET #status = :status, StoppedAt = :stopped_at",
            ExpressionAttributeNames={"#status": "Status"},
            ExpressionAttributeValues={
                ":status": "TERMINATING",
                ":stopped_at": stopped_at,
            },
        )

        return response(
            200,
            {
                "message": "Instance termination requested",
                "challenge_id": challenge_id,
                "instance_id": instance_id,
                "status": "TERMINATING",
                "stopped_at": stopped_at,
            },
        )

    except Exception as exc:
        import traceback

        print("ERROR:", str(exc))
        print(traceback.format_exc())
        return response(500, {"error": str(exc)})


def _parse_body(event):
    body = event.get("body") or "{}"
    if isinstance(body, dict):
        return body
    return json.loads(body)


def _get_user_id(event, body):
    jwt_claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    lambda_claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})

    return str(
        jwt_claims.get("sub")
        or lambda_claims.get("sub")
        or lambda_claims.get("user_id")
        or body.get("user_id")
        or ""
    ).strip()


def response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "content-type,authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body),
    }
