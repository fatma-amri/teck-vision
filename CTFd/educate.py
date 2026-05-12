"""Player-facing educate routes (same behavior as rooms, filtered section)."""

import logging

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import func

from CTFd.constants.config import ChallengeVisibilityTypes, Configs
from CTFd.models import RoomChallenge, RoomSolve, Rooms, Users, db
from CTFd.utils.aws_ova import resolve_aws_challenge_id_for_room
from CTFd.utils.config import is_teams_mode
from CTFd.utils.decorators import authed_only, require_complete_profile, require_verified_emails
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.user import authed, get_current_team, get_current_user

logger = logging.getLogger(__name__)

educate = Blueprint("educate", __name__)
EDUCATE_SLUG_PREFIX = "educate-"


def _educate_query():
    return Rooms.query.filter(Rooms.is_active.is_(True)).filter(
        Rooms.slug.like(f"{EDUCATE_SLUG_PREFIX}%")
    )


@educate.route("/educate/", methods=["GET"])
@require_complete_profile
@require_verified_emails
@check_challenge_visibility
def educate_listing():
    if not (
        Configs.challenge_visibility == ChallengeVisibilityTypes.PUBLIC
        and authed() is False
    ):
        if is_teams_mode() and get_current_team() is None:
            return redirect(url_for("teams.private", next=request.full_path))

    all_rooms = _educate_query().order_by(Rooms.id.asc()).all()
    user = get_current_user() if authed() else None
    room_list = []
    for room in all_rooms:
        challenges = room.challenges.all()
        challenge_ids = [c.id for c in challenges]
        total = len(challenges)

        players_count = 0
        if challenge_ids:
            players_count = (
                db.session.query(func.count(func.distinct(RoomSolve.user_id)))
                .filter(RoomSolve.challenge_id.in_(challenge_ids))
                .scalar()
                or 0
            )

        solved_count = 0
        if user and challenge_ids:
            solved_count = (
                RoomSolve.query.filter(
                    RoomSolve.user_id == user.id,
                    RoomSolve.challenge_id.in_(challenge_ids),
                ).count()
            )

        room_list.append(
            {
                "id": room.id,
                "name": room.name,
                "slug": room.slug,
                "description": room.description,
                "difficulty": room.difficulty,
                "duration": room.duration,
                "total_challenges": total,
                "players_count": players_count,
                "solved_count": solved_count,
            }
        )

    return render_template(
        "rooms.html",
        rooms=room_list,
        section_title="Educate",
        section_kicker="Learning Paths",
        section_subtitle="Choose an education room, launch the environment, and learn step-by-step.",
        room_detail_endpoint="educate.educate_detail",
    )


@educate.route("/educate/<slug>", methods=["GET"])
@require_complete_profile
@require_verified_emails
@check_challenge_visibility
def educate_detail(slug):
    if not (
        Configs.challenge_visibility == ChallengeVisibilityTypes.PUBLIC
        and authed() is False
    ):
        if is_teams_mode() and get_current_team() is None:
            return redirect(url_for("teams.private", next=request.full_path))

    room = _educate_query().filter_by(slug=slug).first_or_404()
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
            "rank": i + 1,
            "id": row.id,
            "name": row.name,
            "solve_count": row.solve_count,
            "completed_at": row.completed_at,
        }
        for i, row in enumerate(completed_rows)
    ]

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
        challenge_target_ip=room.target_ip or None,
        machine_challenge_id=machine_challenge_id,
    )


@educate.route("/learn/<slug>")
@authed_only
def educate_legacy_redirect(slug):
    return redirect(url_for("educate.educate_detail", slug=slug))

