import json
import os
import time

import boto3


ec2 = boto3.client("ec2")
dynamodb = boto3.resource("dynamodb")

SESSION_TABLE_NAME = os.environ.get("SESSION_TABLE_NAME", "CTFChallenges")
OVA_TABLE_NAME = os.environ.get("OVA_TABLE_NAME", "ctf-ova-imports")
INSTANCE_TYPE = os.environ.get("INSTANCE_TYPE", "t3.micro")
KEY_NAME = os.environ.get("KEY_NAME", "ctf")
SUBNET_ID = os.environ.get("SUBNET_ID", "subnet-0ef9bef6cbe3b556b")
SECURITY_GROUP_ID = os.environ.get("SECURITY_GROUP_ID", "sg-00926707e3e049019")
SESSION_SECONDS = int(os.environ.get("SESSION_SECONDS", "3600"))

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

session_table = dynamodb.Table(SESSION_TABLE_NAME)
ova_table = dynamodb.Table(OVA_TABLE_NAME)


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
        if existing.get("Item", {}).get("Status") == "RUNNING":
            item = existing["Item"]
            return response(
                200,
                {
                    "message": "Instance already running for this user",
                    "instance_id": item.get("InstanceID"),
                    "public_ip": item.get("PublicIP"),
                    "expires_at": int(item.get("ExpiresAt", 0)),
                },
            )

        ami_id = _get_ami_id(challenge_id)
        now = int(time.time())
        expires_at = now + SESSION_SECONDS

        instance = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=INSTANCE_TYPE,
            MinCount=1,
            MaxCount=1,
            KeyName=KEY_NAME,
            SubnetId=SUBNET_ID,
            SecurityGroupIds=[SECURITY_GROUP_ID],
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [
                        {"Key": "UserID", "Value": user_id},
                        {"Key": "ChallengeID", "Value": challenge_id},
                        {"Key": "ExpiresAt", "Value": str(expires_at)},
                    ],
                }
            ],
            UserData=USER_DATA,
        )

        instance_id = instance["Instances"][0]["InstanceId"]
        ec2.get_waiter("instance_running").wait(InstanceIds=[instance_id])
        public_ip = _get_public_ip(instance_id)

        if not public_ip:
            return response(500, {"error": "Instance started but no public IP yet"})

        session_table.put_item(
            Item={
                "ChallengeID": challenge_id,
                "UserID": user_id,
                "InstanceID": instance_id,
                "PublicIP": public_ip,
                "Status": "RUNNING",
                "StartedAt": now,
                "ExpiresAt": expires_at,
                "AmiID": ami_id,
            }
        )

        return response(
            200,
            {
                "challenge_id": challenge_id,
                "ami_id": ami_id,
                "instance_id": instance_id,
                "public_ip": public_ip,
                "expires_at": expires_at,
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


def _get_ami_id(challenge_id):
    ova_response = ova_table.get_item(Key={"challenge_id": challenge_id})
    item = ova_response.get("Item")

    if not item:
        legacy_response = session_table.get_item(
            Key={"ChallengeID": challenge_id, "UserID": "admin"}
        )
        item = legacy_response.get("Item")

    if not item:
        raise ValueError(f"Challenge {challenge_id} is not linked to an AMI")

    status = item.get("import_status", "completed")
    ami_id = item.get("ami_id") or item.get("AmiID")

    if status != "completed" or not ami_id:
        raise ValueError(f"Challenge {challenge_id} AMI is not ready yet")

    return ami_id


def _get_public_ip(instance_id):
    public_ip = None
    attempts = 0
    while not public_ip and attempts < 10:
        time.sleep(3)
        desc = ec2.describe_instances(InstanceIds=[instance_id])
        instance_data = desc["Reservations"][0]["Instances"][0]
        public_ip = instance_data.get("PublicIpAddress")
        attempts += 1
    return public_ip


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
