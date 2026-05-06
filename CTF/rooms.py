"""Player-facing room routes."""

import logging

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from sqlalchemy import func

from CTFd.cache import cache
from CTFd.constants.config import ChallengeVisibilityTypes, Configs
from CTFd.models import Challenges, RoomChallenge, RoomSolve, Rooms, Solves, db
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

    if not all_rooms:
        return render_template("rooms.html", rooms=[])

    room_ids = [r.id for r in all_rooms]

    # Load all challenges for all rooms in one query
    all_challenges = RoomChallenge.query.filter(
        RoomChallenge.room_id.in_(room_ids)
    ).all()

    room_challenge_ids = {}  # room_id -> [challenge_id, ...]
    for c in all_challenges:
        room_challenge_ids.setdefault(c.room_id, []).append(c.id)

    all_challenge_ids = [c.id for c in all_challenges]

    # Count unique players per room in one query (challenge_id -> set of user_ids)
    room_player_sets = {}  # room_id -> set of user_ids
    if all_challenge_ids:
        challenge_to_room = {c.id: c.room_id for c in all_challenges}
        solve_rows = (
            db.session.query(RoomSolve.challenge_id, RoomSolve.user_id)
            .filter(RoomSolve.challenge_id.in_(all_challenge_ids))
            .distinct()
            .all()
        )
        for cid, uid in solve_rows:
            rid = challenge_to_room[cid]
            room_player_sets.setdefault(rid, set()).add(uid)

    # Load current user's solved challenge IDs in one query
    user_solved_ids = set()
    if user and all_challenge_ids:
        user_solved_ids = {
            rs.challenge_id
            for rs in RoomSolve.query.filter(
                RoomSolve.user_id == user.id,
                RoomSolve.challenge_id.in_(all_challenge_ids),
            ).all()
        }

    room_list = []
    for room in all_rooms:
        cids = room_challenge_ids.get(room.id, [])
        total = len(cids)
        players_count = len(room_player_sets.get(room.id, set()))
        solved_count = sum(1 for cid in cids if cid in user_solved_ids)

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
    else:
        players_count = 0

    target_ip = room.target_ip or None

    # Linked standard CTFd challenges
    linked = Challenges.query.filter_by(room_id=room.id, state="visible").order_by(Challenges.id.asc()).all()
    linked_ids = [c.id for c in linked]
    ctfd_solved_ids = set()
    if user and linked_ids:
        ctfd_solved_ids = {
            s.challenge_id
            for s in Solves.query.filter(
                Solves.user_id == user.id,
                Solves.challenge_id.in_(linked_ids),
            ).all()
        }
    linked_cards = [
        {
            "id": c.id,
            "title": c.name,
            "description": c.description or "",
            "points": c.value,
            "category": c.category or "",
            "solved": c.id in ctfd_solved_ids,
            "type": "ctfd",
        }
        for c in linked
    ]

    return render_template(
        "room_detail.html",
        room=room,
        room_slug=room.slug,
        challenges=challenge_cards,
        linked_challenges=linked_cards,
        solved_count=solved_count,
        total_count=total_count,
        progress_percent=progress_percent,
        players_count=players_count,
        challenge_target_ip=target_ip,
    )


# Legacy redirect: /play/<slug> → /rooms/<slug>
@rooms.route("/play/<slug>")
@authed_only
def play_redirect(slug):
    return redirect(url_for("rooms.room_detail", slug=slug))
