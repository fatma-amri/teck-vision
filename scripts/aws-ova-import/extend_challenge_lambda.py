import json
import os
import time
from decimal import Decimal

import boto3


dynamodb = boto3.resource("dynamodb")

SESSION_TABLE_NAME = os.environ.get("SESSION_TABLE_NAME", "CTFChallenges")
EXTENSION_SECONDS = int(os.environ.get("EXTENSION_SECONDS", "3600"))
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
            return response(404, {"error": "Session not found"})

        if item.get("Status") != "RUNNING":
            return response(
                409,
                {
                    "error": "Session is not running",
                    "status": item.get("Status"),
                },
            )

        now = int(time.time())
        current_expiry = int(item.get("ExpiresAt", now))
        new_expiry = max(current_expiry, now) + EXTENSION_SECONDS

        session_table.update_item(
            Key={"ChallengeID": challenge_id, "UserID": user_id},
            UpdateExpression="SET ExpiresAt = :expires_at, UpdatedAt = :updated_at",
            ExpressionAttributeValues={
                ":expires_at": Decimal(new_expiry),
                ":updated_at": Decimal(now),
            },
        )

        return response(
            200,
            {
                "message": "Time extended",
                "challenge_id": challenge_id,
                "instance_id": item.get("InstanceID"),
                "public_ip": item.get("PublicIP"),
                "expires_at": new_expiry,
                "added_seconds": EXTENSION_SECONDS,
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
