import os
import re
from urllib.parse import urlparse

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app

from CTFd.utils import get_app_config


DEFAULT_OVA_TABLE = "ctf-ova-imports"
DEFAULT_EDUCATE_OVA_TABLE = "ctf-educate-ova-imports"
DEFAULT_OVA_REGION = "eu-west-3"
DEFAULT_SESSION_TABLE = "CTFChallenges"


def resolve_aws_challenge_id_for_room(room):
    if room.aws_challenge_id:
        return room.aws_challenge_id

    s3_location = _extract_ova_location(room.description or "")
    if not s3_location:
        return None

    parsed = _parse_s3_location(s3_location)
    if not parsed:
        return None

    bucket, key = parsed
    item = _find_ova_import(bucket=bucket, key=key)
    if not item:
        return None

    challenge_id = item.get("challenge_id")
    if challenge_id:
        room.aws_challenge_id = challenge_id

    return challenge_id


def get_running_aws_session(challenge_id, user_id):
    if not challenge_id or not user_id:
        return None

    table_name = _get_config("AWS_SESSION_TABLE", _get_config("SESSION_TABLE_NAME", DEFAULT_SESSION_TABLE))
    region = _get_config("OVA_S3_REGION", _get_config("AWS_S3_REGION", DEFAULT_OVA_REGION))

    try:
        table = boto3.resource("dynamodb", region_name=region).Table(table_name)
        response = table.get_item(Key={"ChallengeID": str(challenge_id), "UserID": str(user_id)})
        item = response.get("Item")
        if item and item.get("Status") == "RUNNING":
            return item
    except (BotoCoreError, ClientError) as exc:
        current_app.logger.warning("Could not read AWS session for %s/%s: %s", challenge_id, user_id, exc)

    return None


def _extract_ova_location(description):
    match = re.search(r"OVA Image:\s*(s3://\S+)", description)
    return match.group(1).strip() if match else None


def _parse_s3_location(location):
    parsed = urlparse(location)
    if parsed.scheme != "s3" or not parsed.netloc or not parsed.path:
        return None

    return parsed.netloc, parsed.path.lstrip("/")


def _find_ova_import(bucket, key):
    table_name = _resolve_ova_table_name_from_s3(bucket=bucket, key=key)
    region = _resolve_ova_region_from_s3(bucket=bucket, key=key)

    try:
        table = boto3.resource("dynamodb", region_name=region).Table(table_name)
        response = table.scan(
            FilterExpression=Attr("s3_bucket").eq(bucket) & Attr("s3_key").eq(key),
            Limit=1,
        )
        items = response.get("Items", [])
        return items[0] if items else None
    except (BotoCoreError, ClientError) as exc:
        current_app.logger.warning("Could not resolve OVA import for %s/%s: %s", bucket, key, exc)
        return None


def _get_config(name, default=None):
    return current_app.config.get(name) or get_app_config(name) or os.environ.get(name) or default


def _resolve_ova_table_name_from_s3(bucket, key):
    educate_bucket = _get_config("EDUCATE_OVA_S3_BUCKET", "ctf-tekup-educate")
    educate_prefix = _get_config("EDUCATE_OVA_S3_PREFIX", "educate_ovas").strip("/")
    if bucket == educate_bucket and key.startswith(f"{educate_prefix}/"):
        return _get_config("EDUCATE_OVA_IMPORTS_TABLE", DEFAULT_EDUCATE_OVA_TABLE)
    return _get_config("OVA_IMPORTS_TABLE", DEFAULT_OVA_TABLE)


def _resolve_ova_region_from_s3(bucket, key):
    educate_bucket = _get_config("EDUCATE_OVA_S3_BUCKET", "ctf-tekup-educate")
    educate_prefix = _get_config("EDUCATE_OVA_S3_PREFIX", "educate_ovas").strip("/")
    if bucket == educate_bucket and key.startswith(f"{educate_prefix}/"):
        return _get_config("EDUCATE_OVA_S3_REGION", DEFAULT_OVA_REGION)
    return _get_config("OVA_S3_REGION", _get_config("AWS_S3_REGION", DEFAULT_OVA_REGION))
