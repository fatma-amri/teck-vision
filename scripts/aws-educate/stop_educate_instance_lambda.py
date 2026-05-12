import json
import os
import time
from typing import Any, Dict

import boto3


ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")

SESSION_TABLE_NAME = os.environ.get("SESSION_TABLE_NAME", "EducateChallenges")
session_table = dynamodb.Table(SESSION_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = _parse_body(event)
        challenge_id = str(body.get("challenge_id") or body.get("room_id") or "").strip()
        user_id = _get_user_id(event, body)

        if not challenge_id:
            return _response(400, {"success": False, "error": "Missing challenge_id"})
        if not user_id:
            return _response(401, {"success": False, "error": "Missing authenticated user_id"})

        item = session_table.get_item(
            Key={"ChallengeID": challenge_id, "UserID": user_id}
        ).get("Item")
        if not item:
            return _response(404, {"success": False, "error": "No running instance found"})

        instance_id = item.get("InstanceID")
        if not instance_id:
            return _response(400, {"success": False, "error": "No instance linked to this session"})

        current_status = str(item.get("Status", "")).upper()
        if current_status in {"STOPPED", "TERMINATED", "TERMINATING"}:
            return _response(
                200,
                {
                    "success": True,
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

        return _response(
            200,
            {
                "success": True,
                "message": "Instance termination requested",
                "challenge_id": challenge_id,
                "instance_id": instance_id,
                "status": "TERMINATING",
                "stopped_at": stopped_at,
            },
        )
    except Exception as exc:  # pragma: no cover
        return _response(500, {"success": False, "error": str(exc)})


def _parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if body is None:
        return {}
    if isinstance(body, dict):
        return body
    if isinstance(body, str) and body.strip():
        return json.loads(body)
    return {}


def _get_user_id(event: Dict[str, Any], body: Dict[str, Any]) -> str:
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


def _response(status: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "content-type,authorization",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(payload),
    }
