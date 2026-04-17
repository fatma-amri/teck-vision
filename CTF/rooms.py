"""Room detail views (TryHackMe-like functionality)."""

from flask import Blueprint, render_template
from CTFd.models import Challenges, Solves
from CTFd.utils.decorators import authed_only
from CTFd.utils.user import get_current_user, get_current_team

rooms = Blueprint("rooms", __name__, url_prefix="/play")


@rooms.route("/<room_slug>")
@authed_only
def detail(room_slug):
    """Display a room with its challenges."""
    from flask import abort
    
    # Map room slugs to challenge categories
    ROOMS = {
        "web-security-challenge": "Web Security Challenge",
    }
    
    category = ROOMS.get(room_slug)
    if not category:
        abort(404)
    
    user = get_current_user()
    team = get_current_team()
    account_id = team.id if team else user.id
    account_type = "team" if team else "user"
    
    # Get challenges
    challenges = Challenges.query.filter_by(category=category).all()
    
    # Mark solved challenges
    for challenge in challenges:
        if account_type == "team":
            challenge.solved = bool(Solves.query.filter_by(
                challenge_id=challenge.id, team_id=account_id).first())
        else:
            challenge.solved = bool(Solves.query.filter_by(
                challenge_id=challenge.id, user_id=account_id).first())
    
    solved_count = sum(1 for c in challenges if c.solved)
    total_count = len(challenges)
    progress_percent = int((solved_count / total_count * 100) if total_count else 0)
    
    return render_template(
        "room_simple.html",
        room_slug=room_slug,
        room_name=category,
        challenges=challenges,
        solved_count=solved_count,
        total_count=total_count,
        progress_percent=progress_percent
    )


