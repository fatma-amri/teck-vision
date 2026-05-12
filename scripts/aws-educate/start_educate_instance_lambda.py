import json
import os
import time
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError


ec2 = boto3.client("ec2")

DEFAULT_AMI_ID = os.environ.get("AMI_ID", "").strip()
SUBNET_ID = os.environ["PRIVATE_SUBNET_ID"]
SECURITY_GROUP_ID = os.environ["PRIVATE_SECURITY_GROUP_ID"]
INSTANCE_TYPE = os.environ.get("INSTANCE_TYPE", "t3.micro")
KEY_NAME = os.environ.get("KEY_NAME", "")
INSTANCE_PROFILE_ARN = os.environ.get("EC2_INSTANCE_PROFILE_ARN", "")
WAIT_FOR_RUNNING_SECONDS = int(os.environ.get("WAIT_FOR_RUNNING_SECONDS", "30"))


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = _parse_body(event)
        user_id = str(body.get("user_id", "anonymous")).strip() or "anonymous"
        room_id = str(body.get("room_id", "educate-room")).strip() or "educate-room"
        ami_id = str(body.get("ami_id", DEFAULT_AMI_ID)).strip()

        if not ami_id:
            return _response(
                400,
                {
                    "success": False,
                    "error": "No AMI configured yet. Provide ami_id in request body or set AMI_ID env var.",
                },
            )

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
                        {"Key": "Name", "Value": f"educate-{room_id}-{user_id}"},
                        {"Key": "Section", "Value": "educate"},
                        {"Key": "RoomId", "Value": room_id},
                        {"Key": "UserId", "Value": user_id},
                    ],
                }
            ],
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

        return _response(
            200,
            {
                "success": True,
                "instance_id": instance_id,
                "state": state,
                "private_ip": private_ip,
                "ami_id": ami_id,
                "subnet_id": SUBNET_ID,
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
