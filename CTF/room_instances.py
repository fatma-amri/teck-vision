"""Room instances and machine control endpoints."""

import datetime
import logging

from flask import Blueprint, abort, jsonify, request

from flask import current_app

from CTFd.models import RoomInstances, Rooms, db
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_team, get_current_user

logger = logging.getLogger(__name__)

room_instances = Blueprint("room_instances", __name__, url_prefix="/api/room-instances")

# Map room slugs to challenge categories
ROOM_MAPPING = {
    "web-security-challenge": "Web Security Challenge",
    "lazyadmin": "lazyadmin",
}


def get_room_category(room_slug):
    """Convert room slug to category name."""
    category = ROOM_MAPPING.get(room_slug)
    if not category:
        return None
    return category


@room_instances.route("/start/<room_slug>", methods=["POST"])
@authed_only
def start_machine(room_slug):
    """Start a machine instance for a room.
    
    Args:
        room_slug: The room slug (e.g., 'web-security-challenge')
        
    Returns:
        JSON response with machine IP, duration, and expiration time
    """
    room_category = get_room_category(room_slug)
    if not room_category:
        abort(404)
    
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
    
    # Resolve target IP: Room model > config fallback
    room_model = Rooms.query.filter_by(slug=room_slug).first()
    machine_ip = (
        room_model.target_ip
        if room_model and room_model.target_ip
        else current_app.config.get("CHALLENGE_TARGET_IP", "15.237.60.47")
    )

    if existing:
        return jsonify({
            "success": True,
            "ip": existing.machine_ip,
            "machine_ip": existing.machine_ip,
            "started_at": existing.started_at.isoformat() if existing.started_at else None,
            "expires_at": existing.expires_at.isoformat() if existing.expires_at else None,
            "time_remaining": existing.time_remaining_seconds,
            "duration_minutes": existing.duration_minutes,
        }), 200

    # Create new machine instance
    now = datetime.datetime.utcnow()
    duration = room_model.duration if room_model else 30
    expires_at = now + datetime.timedelta(minutes=duration)

    instance = RoomInstances(
        user_id=user.id if account_type == "user" else None,
        team_id=team.id if account_type == "team" else None,
        category=room_category,
        machine_ip=machine_ip,
        is_active=True,
        started_at=now,
        expires_at=expires_at,
        duration_minutes=duration,
    )

    db.session.add(instance)
    db.session.commit()

    logger.info(f"Machine started: room={room_slug}, {account_type}_id={account_id}")

    return jsonify({
        "success": True,
        "ip": instance.machine_ip,
        "machine_ip": instance.machine_ip,
        "started_at": instance.started_at.isoformat(),
        "expires_at": instance.expires_at.isoformat(),
        "time_remaining": instance.time_remaining_seconds,
        "duration_minutes": instance.duration_minutes,
    }), 201


@room_instances.route("/terminate/<room_slug>", methods=["POST"])
@authed_only
def terminate_machine(room_slug):
    """Terminate a machine instance for a room.
    
    Args:
        room_slug: The room slug (e.g., 'web-security-challenge')
        
    Returns:
        JSON success response
    """
    room_category = get_room_category(room_slug)
    if not room_category:
        abort(404)
    
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
    
    logger.info(f"Machine terminated: room={room_slug}, category={room_category}, {account_type}_id={account_id}")
    
    return jsonify({"success": True}), 200


@room_instances.route("/status/<room_slug>", methods=["GET"])
@authed_only
def check_machine_status(room_slug):
    """Check the status of a machine instance.
    
    Args:
        room_slug: The room slug (e.g., 'web-security-challenge')
        
    Returns:
        JSON with machine status and remaining time
    """
    room_category = get_room_category(room_slug)
    if not room_category:
        abort(404)
    
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

