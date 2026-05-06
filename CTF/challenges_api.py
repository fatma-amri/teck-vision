"""API endpoints for room challenge flag submission."""

import logging

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from CTFd.models import Awards, RoomChallenge, RoomInstances, RoomSolve, db
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_team, get_current_user

logger = logging.getLogger(__name__)

challenges_api = Blueprint("challenges_api", __name__, url_prefix="/api/challenges")


@challenges_api.route("/<int:challenge_id>/attempt", methods=["POST"])
@authed_only
def submit_room_flag(challenge_id):
    """Submit a flag for a room challenge.

    Expected JSON: {"flag": "flag_value"}

    Returns JSON:
        200 {"success": true,  "message": "Correct!", "points": X}
        400 {"success": false, "message": "Wrong flag, try again"}
        403 {"success": false, "message": "Start the machine first"}
        409 {"success": false, "message": "Already solved"}
    """
    user = get_current_user()

    challenge = db.session.get(RoomChallenge, challenge_id)
    if not challenge:
        return jsonify({"success": False, "message": "Challenge not found"}), 404

    # Check already solved
    existing = RoomSolve.query.filter_by(
        user_id=user.id, challenge_id=challenge_id
    ).first()
    if existing:
        return jsonify({"success": False, "message": "Already solved"}), 409

    # Require an active machine for the room this challenge belongs to
    room = challenge.room
    team = get_current_team()
    if team:
        active_instance = RoomInstances.query.filter(
            RoomInstances.is_active == True,
            RoomInstances.team_id == team.id,
            or_(
                RoomInstances.category == room.slug,
                RoomInstances.category == room.name,
            ),
        ).first()
    else:
        active_instance = RoomInstances.query.filter(
            RoomInstances.is_active == True,
            RoomInstances.user_id == user.id,
            or_(
                RoomInstances.category == room.slug,
                RoomInstances.category == room.name,
            ),
        ).first()

    if not active_instance:
        return jsonify({"success": False, "message": "Start the machine first"}), 403

    data = request.get_json(silent=True) or {}
    submitted = (data.get("flag") or "").strip()

    if not submitted:
        return jsonify({"success": False, "message": "No flag provided"}), 400

    if submitted.lower() != (challenge.answer or "").lower():
        logger.info(
            "Wrong flag: challenge=%d user=%d submitted=%r",
            challenge_id,
            user.id,
            submitted,
        )
        return jsonify({"success": False, "message": "Wrong flag, try again"}), 400

    # Correct flag — record solve and award points on the scoreboard
    try:
        solve = RoomSolve(user_id=user.id, challenge_id=challenge_id)
        db.session.add(solve)

        award = Awards(
            user_id=user.id,
            team_id=team.id if team else None,
            name=challenge.title,
            description=f"Solved in room: {room.name}",
            value=challenge.points,
            category=room.name,
        )
        db.session.add(award)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Error saving solve: %s", exc)
        return jsonify({"success": False, "message": "Server error"}), 500

    logger.info("Correct flag: challenge=%d user=%d", challenge_id, user.id)
    return jsonify({"success": True, "message": "Correct!", "points": challenge.points}), 200
