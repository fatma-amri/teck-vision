import json
import os
import time
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError


ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")

DEFAULT_AMI_ID = os.environ.get("AMI_ID", "").strip()
SUBNET_ID = os.environ["PRIVATE_SUBNET_ID"]
SECURITY_GROUP_ID = os.environ["PRIVATE_SECURITY_GROUP_ID"]
INSTANCE_TYPE = os.environ.get("INSTANCE_TYPE", "t3.micro")
KEY_NAME = os.environ.get("KEY_NAME", "")
INSTANCE_PROFILE_ARN = os.environ.get("EC2_INSTANCE_PROFILE_ARN", "")
WAIT_FOR_RUNNING_SECONDS = int(os.environ.get("WAIT_FOR_RUNNING_SECONDS", "30"))
USER_DATA = """#!/bin/bash
# Install CloudWatch Agent
if [ -f /etc/redhat-release ]; then
    yum install -y amazon-cloudwatch-agent
elif [ -f /etc/debian_version ]; then
    apt-get update
    apt-get install -y wget
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
    dpkg -i -E ./amazon-cloudwatch-agent.deb
fi

# Start CloudWatch Agent with default config
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c default
"""
SESSION_TABLE_NAME = os.environ.get("SESSION_TABLE_NAME", "EducateChallenges")
SESSION_SECONDS = int(os.environ.get("SESSION_SECONDS", "3600"))

session_table = dynamodb.Table(SESSION_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = _parse_body(event)
        user_id = _get_user_id(event, body)
        challenge_id = str(body.get("challenge_id") or body.get("room_id") or "").strip()
        ami_id = str(body.get("ami_id", DEFAULT_AMI_ID)).strip()

        if not challenge_id:
            return _response(400, {"success": False, "error": "Missing challenge_id"})

        if not user_id:
            return _response(401, {"success": False, "error": "Missing authenticated user_id"})

        if not ami_id:
            return _response(
                400,
                {
                    "success": False,
                    "error": "No AMI configured yet. Provide ami_id in request body or set AMI_ID env var.",
                },
            )

        existing = session_table.get_item(
            Key={"ChallengeID": challenge_id, "UserID": user_id}
        ).get("Item")
        if existing and existing.get("Status") == "RUNNING":
            return _response(
                200,
                {
                    "success": True,
                    "message": "Instance already running for this user",
                    "instance_id": existing.get("InstanceID"),
                    "private_ip": existing.get("PrivateIP"),
                    "expires_at": int(existing.get("ExpiresAt", 0)),
                },
            )

        now = int(time.time())
        expires_at = now + SESSION_SECONDS
        params: Dict[str, Any] = {
            "ImageId": ami_id,
            "InstanceType": INSTANCE_TYPE,
            "MinCount": 1,
            "MaxCount": 1,
            "SubnetId": SUBNET_ID,
            "SecurityGroupIds": [SECURITY_GROUP_ID],
            "TagSpecifications": [
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "Name", "Value": f"educate-{challenge_id}-{user_id}"},
                        {"Key": "Section", "Value": "educate"},
                        {"Key": "ChallengeID", "Value": challenge_id},
                        {"Key": "UserId", "Value": user_id},
                        {"Key": "ExpiresAt", "Value": str(expires_at)},
                    ],
                }
            ],
            "UserData": USER_DATA,
        }

        if KEY_NAME:
            params["KeyName"] = KEY_NAME
        if INSTANCE_PROFILE_ARN:
            params["IamInstanceProfile"] = {"Arn": INSTANCE_PROFILE_ARN}

        # Force private-only interface. Instance remains in private subnet.
        params["NetworkInterfaces"] = [
            {
                "DeviceIndex": 0,
                "SubnetId": SUBNET_ID,
                "Groups": [SECURITY_GROUP_ID],
                "AssociatePublicIpAddress": False,
                "DeleteOnTermination": True,
            }
        ]
        params.pop("SubnetId", None)
        params.pop("SecurityGroupIds", None)

        run_response = ec2.run_instances(**params)
        instance_id = run_response["Instances"][0]["InstanceId"]

        state = "pending"
        private_ip = None
        deadline = time.time() + WAIT_FOR_RUNNING_SECONDS
        while time.time() < deadline:
            desc = ec2.describe_instances(InstanceIds=[instance_id])
            instance = desc["Reservations"][0]["Instances"][0]
            state = instance["State"]["Name"]
            private_ip = instance.get("PrivateIpAddress")
            if state == "running":
                break
            time.sleep(3)

        session_table.put_item(
            Item={
                "ChallengeID": challenge_id,
                "UserID": user_id,
                "InstanceID": instance_id,
                "PrivateIP": private_ip or "",
                "Status": "RUNNING" if state == "running" else state.upper(),
                "StartedAt": now,
                "ExpiresAt": expires_at,
                "AmiID": ami_id,
            }
        )

        return _response(
            200,
            {
                "success": True,
                "challenge_id": challenge_id,
                "instance_id": instance_id,
                "state": state,
                "private_ip": private_ip,
                "ami_id": ami_id,
                "subnet_id": SUBNET_ID,
                "expires_at": expires_at,
            },
        )
    except ClientError as exc:
        return _response(500, {"success": False, "error": str(exc)})
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
