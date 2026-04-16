"""Room instances and machine control endpoints (TryHackMe-like functionality)."""

import datetime
import logging

from flask import Blueprint, abort, jsonify, request

from CTFd.models import RoomInstances, db
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_team, get_current_user

logger = logging.getLogger(__name__)

room_instances = Blueprint("room_instances", __name__, url_prefix="/api/room-instances")


@room_instances.route("/start/<room_category>", methods=["POST"])
@authed_only
def start_machine(room_category):
    """Start a machine instance for a room.
    
    Args:
        room_category: The challenge category/room name
        
    Returns:
        JSON response with machine IP, duration, and expiration time
    """
    user = get_current_user()
    team = get_current_team()
    
    # Check if machine is already active for this user/team
    account_id = team.id if team else user.id
    account_type = "team" if team else "user"
    
    existing = RoomInstances.query.filter_by(
        category=room_category,
        is_active=True,
        team_id=account_id if account_type == "team" else None,
        user_id=account_id if account_type == "user" else None,
    ).first()
    
    if existing:
        # Machine already active - return its details
        return jsonify({
            "success": True,
            "machine_ip": existing.machine_ip,
            "started_at": existing.started_at.isoformat() if existing.started_at else None,
            "expires_at": existing.expires_at.isoformat() if existing.expires_at else None,
            "time_remaining": existing.time_remaining_seconds,
            "duration_minutes": existing.duration_minutes,
        }), 200
    
    # Create new machine instance
    now = datetime.datetime.utcnow()
    duration = 30  # Default 30 minutes
    expires_at = now + datetime.timedelta(minutes=duration)
    
    instance = RoomInstances(
        user_id=user.id if account_type == "user" else None,
        team_id=team.id if account_type == "team" else None,
        category=room_category,
        machine_ip="15.237.60.47",  # Static IP
        is_active=True,
        started_at=now,
        expires_at=expires_at,
        duration_minutes=duration,
    )
    
    db.session.add(instance)
    db.session.commit()
    
    logger.info(f"Machine started: room={room_category}, {account_type}_id={account_id}")
    
    return jsonify({
        "success": True,
        "machine_ip": instance.machine_ip,
        "started_at": instance.started_at.isoformat(),
        "expires_at": instance.expires_at.isoformat(),
        "time_remaining": instance.time_remaining_seconds,
        "duration_minutes": instance.duration_minutes,
    }), 201


@room_instances.route("/terminate/<room_category>", methods=["POST"])
@authed_only
def terminate_machine(room_category):
    """Terminate a machine instance for a room.
    
    Args:
        room_category: The challenge category/room name
        
    Returns:
        JSON success response
    """
    user = get_current_user()
    team = get_current_team()
    
    account_id = team.id if team else user.id
    account_type = "team" if team else "user"
    
    instance = RoomInstances.query.filter_by(
        category=room_category,
        is_active=True,
        team_id=account_id if account_type == "team" else None,
        user_id=account_id if account_type == "user" else None,
    ).first()
    
    if not instance:
        return jsonify({"success": False, "message": "No active machine"}), 404
    
    instance.is_active = False
    db.session.commit()
    
    logger.info(f"Machine terminated: room={room_category}, {account_type}_id={account_id}")
    
    return jsonify({"success": True}), 200


@room_instances.route("/status/<room_category>", methods=["GET"])
@authed_only
def check_machine_status(room_category):
    """Check the status of a machine instance.
    
    Args:
        room_category: The challenge category/room name
        
    Returns:
        JSON with machine status and remaining time
    """
    user = get_current_user()
    team = get_current_team()
    
    account_id = team.id if team else user.id
    account_type = "team" if team else "user"
    
    instance = RoomInstances.query.filter_by(
        category=room_category,
        is_active=True,
        team_id=account_id if account_type == "team" else None,
        user_id=account_id if account_type == "user" else None,
    ).first()
    
    if not instance:
        return jsonify({
            "is_active": False,
            "machine_ip": None,
            "time_remaining": 0,
        }), 200
    
    # Check if expired
    now = datetime.datetime.utcnow()
    if instance.expires_at and now > instance.expires_at:
        instance.is_active = False
        db.session.commit()
        return jsonify({
            "is_active": False,
            "machine_ip": None,
            "time_remaining": 0,
        }), 200
    
    return jsonify({
        "is_active": True,
        "machine_ip": instance.machine_ip,
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "expires_at": instance.expires_at.isoformat() if instance.expires_at else None,
        "time_remaining": instance.time_remaining_seconds,
        "duration_minutes": instance.duration_minutes,
    }), 200
