"""Player-facing room routes."""

import logging

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from sqlalchemy import func

from CTFd.cache import cache
from CTFd.constants.config import ChallengeVisibilityTypes, Configs
from CTFd.models import RoomChallenge, RoomSolve, Rooms, Users, db
from CTFd.utils.aws_ova import resolve_aws_challenge_id_for_room
from CTFd.utils.config import is_teams_mode
from CTFd.utils.decorators import authed_only, require_complete_profile, require_verified_emails
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.user import authed, get_current_team, get_current_user

logger = logging.getLogger(__name__)

rooms = Blueprint("rooms", __name__)


# ── Rooms listing ─────────────────────────────────────────────────────────────

@rooms.route("/rooms/", methods=["GET"])
@require_complete_profile
@require_verified_emails
@check_challenge_visibility
def rooms_listing():
    if (
        Configs.challenge_visibility == ChallengeVisibilityTypes.PUBLIC
        and authed() is False
    ):
        pass
    else:
        if is_teams_mode() and get_current_team() is None:
            return redirect(url_for("teams.private", next=request.full_path))

    all_rooms = Rooms.query.filter_by(is_active=True).order_by(Rooms.id.asc()).all()

    user = get_current_user() if authed() else None
    room_list = []
    for room in all_rooms:
        challenges = room.challenges.all()
        total = len(challenges)
        challenge_ids = [c.id for c in challenges]

        # Count unique players who solved at least one challenge in this room
        if challenge_ids:
            players_count = (
                db.session.query(func.count(func.distinct(RoomSolve.user_id)))
                .filter(RoomSolve.challenge_id.in_(challenge_ids))
                .scalar()
                or 0
            )
        else:
            players_count = 0

        # Current user progress
        solved_count = 0
        if user and challenge_ids:
            solved_count = (
                RoomSolve.query.filter(
                    RoomSolve.user_id == user.id,
                    RoomSolve.challenge_id.in_(challenge_ids),
                ).count()
            )

        room_list.append({
            "id": room.id,
            "name": room.name,
            "slug": room.slug,
            "description": room.description,
            "difficulty": room.difficulty,
            "duration": room.duration,
            "total_challenges": total,
            "players_count": players_count,
            "solved_count": solved_count,
        })

    return render_template("rooms.html", rooms=room_list)


# ── Room detail ───────────────────────────────────────────────────────────────

@rooms.route("/rooms/<slug>", methods=["GET"])
@require_complete_profile
@require_verified_emails
@check_challenge_visibility
def room_detail(slug):
    if (
        Configs.challenge_visibility == ChallengeVisibilityTypes.PUBLIC
        and authed() is False
    ):
        pass
    else:
        if is_teams_mode() and get_current_team() is None:
            return redirect(url_for("teams.private", next=request.full_path))

    room = Rooms.query.filter_by(slug=slug, is_active=True).first_or_404()
    needs_machine_link = not room.aws_challenge_id
    machine_challenge_id = resolve_aws_challenge_id_for_room(room)
    if needs_machine_link and machine_challenge_id:
        db.session.commit()

    challenges = room.challenges.order_by(RoomChallenge.position.asc()).all()

    user = get_current_user() if authed() else None
    solved_ids = set()
    if user:
        solved_ids = {
            rs.challenge_id
            for rs in RoomSolve.query.filter(
                RoomSolve.user_id == user.id,
                RoomSolve.challenge_id.in_([c.id for c in challenges]),
            ).all()
        }

    challenge_cards = [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "question": c.question,
            "points": c.points,
            "difficulty": c.difficulty,
            "solved": c.id in solved_ids,
        }
        for c in challenges
    ]

    solved_count = len(solved_ids)
    total_count = len(challenge_cards)
    progress_percent = int((solved_count / total_count) * 100) if total_count else 0

    # Count unique players for this room
    challenge_ids = [c.id for c in challenges]
    if challenge_ids:
        players_count = (
            db.session.query(func.count(func.distinct(RoomSolve.user_id)))
            .filter(RoomSolve.challenge_id.in_(challenge_ids))
            .scalar()
            or 0
        )
        completed_rows = (
            db.session.query(
                Users.id,
                Users.name,
                func.count(func.distinct(RoomSolve.challenge_id)).label("solve_count"),
                func.max(RoomSolve.solved_at).label("completed_at"),
            )
            .join(RoomSolve, RoomSolve.user_id == Users.id)
            .filter(RoomSolve.challenge_id.in_(challenge_ids))
            .group_by(Users.id, Users.name)
            .having(func.count(func.distinct(RoomSolve.challenge_id)) == total_count)
            .order_by(func.max(RoomSolve.solved_at).asc())
            .all()
        )
    else:
        players_count = 0
        completed_rows = []

    completed_users = [
        {
            "rank": index + 1,
            "id": row.id,
            "name": row.name,
            "solve_count": row.solve_count,
            "completed_at": row.completed_at,
        }
        for index, row in enumerate(completed_rows)
    ]

    target_ip = room.target_ip or None

    return render_template(
        "room_detail.html",
        room=room,
        room_slug=room.slug,
        challenges=challenge_cards,
        solved_count=solved_count,
        total_count=total_count,
        progress_percent=progress_percent,
        players_count=players_count,
        completed_users=completed_users,
        challenge_target_ip=target_ip,
        machine_challenge_id=machine_challenge_id,
    )


# Legacy redirect: /play/<slug> → /rooms/<slug>
@rooms.route("/play/<slug>")
@authed_only
def play_redirect(slug):
    return redirect(url_for("rooms.room_detail", slug=slug))
