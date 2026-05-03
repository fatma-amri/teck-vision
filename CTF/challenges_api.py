"""API endpoints for room challenge flag submission."""

import logging

from flask import Blueprint, abort, jsonify, request

from CTFd.models import RoomChallenge, RoomSolve, db
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user

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
        409 {"success": false, "message": "Already solved"}
    """
    user = get_current_user()

    challenge = RoomChallenge.query.get(challenge_id)
    if not challenge:
        return jsonify({"success": False, "message": "Challenge not found"}), 404

    # Check already solved
    existing = RoomSolve.query.filter_by(
        user_id=user.id, challenge_id=challenge_id
    ).first()
    if existing:
        return jsonify({"success": False, "message": "Already solved"}), 409

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
        return jsonify({"success": False, "message": "Wrong flag, try again"}), 200

    # Correct flag — record solve
    try:
        solve = RoomSolve(user_id=user.id, challenge_id=challenge_id)
        db.session.add(solve)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Error saving solve: %s", exc)
        return jsonify({"success": False, "message": "Server error"}), 500

    logger.info("Correct flag: challenge=%d user=%d", challenge_id, user.id)
    return jsonify({"success": True, "message": "Correct!", "points": challenge.points}), 200
