"""API endpoints for room challenges and flag submissions."""

import logging

from flask import Blueprint, abort, jsonify, request

from CTFd.models import Challenges, Flags, Solves, db
from CTFd.plugins.challenges import get_chal_class
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_team, get_current_user

logger = logging.getLogger(__name__)

challenges_api = Blueprint("challenges_api", __name__, url_prefix="/api/challenges")


@challenges_api.route("/<int:challenge_id>/submit-flag", methods=["POST"])
@authed_only
def submit_room_flag(challenge_id):
    """Submit a flag for a room challenge.
    
    Expected JSON: {"flag": "flag_value"}
    
    Returns:
        - 200: {"success": true, "message": "Correct flag!", "points": X}
        - 400: {"success": false, "message": "Wrong flag, try again"}
        - 409: {"success": false, "message": "Challenge already solved"}
    """
    user = get_current_user()
    team = get_current_team()
    
    challenge = Challenges.query.filter_by(id=challenge_id).first()
    if not challenge:
        abort(404)
    
    # Check if already solved
    if team:
        existing_solve = Solves.query.filter_by(
            challenge_id=challenge_id,
            team_id=team.id
        ).first()
    else:
        existing_solve = Solves.query.filter_by(
            challenge_id=challenge_id,
            user_id=user.id
        ).first()
    
    if existing_solve:
        return jsonify({
            "success": False,
            "message": "Challenge already solved"
        }), 409
    
    # Get the flag from request
    data = request.get_json() or {}
    submitted_flag = (data.get("flag") or "").strip()
    
    if not submitted_flag:
        return jsonify({
            "success": False,
            "message": "No flag provided"
        }), 400
    
    # Get all flags for this challenge
    flags = Flags.query.filter_by(challenge_id=challenge_id).all()
    
    # Check if flag is correct (case-insensitive)
    is_correct = False
    for flag_obj in flags:
        if flag_obj.content and submitted_flag.lower() == flag_obj.content.lower():
            is_correct = True
            break
    
    if not is_correct:
        logger.warning(
            f"Wrong flag submitted for challenge {challenge_id}: "
            f"user={user.id}, team={team.id if team else None}, flag={submitted_flag}"
        )
        return jsonify({
            "success": False,
            "message": "Wrong flag, try again"
        }), 400
    
    # Flag is correct - create solve
    try:
        solve = Solves(
            user_id=user.id if not team else None,
            team_id=team.id if team else None,
            challenge_id=challenge_id,
            ip=request.remote_addr,
            provided=submitted_flag,
        )
        
        db.session.add(solve)
        db.session.commit()
        
        logger.info(
            f"Correct flag for challenge {challenge_id}: "
            f"user={user.id}, team={team.id if team else None}"
        )
        
        return jsonify({
            "success": True,
            "message": "Correct flag!",
            "points": challenge.value
        }), 200
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating solve: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Error submitting flag"
        }), 500
