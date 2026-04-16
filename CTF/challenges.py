import re

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from flask_babel import lazy_gettext as _l
from sqlalchemy import func

from CTFd.constants.config import ChallengeVisibilityTypes, Configs
from CTFd.models import Challenges, Solves
from CTFd.utils.config import is_teams_mode
from CTFd.utils.dates import ctf_ended, ctf_paused, ctf_started
from CTFd.utils.decorators import (
    during_ctf_time_only,
    require_complete_profile,
    require_verified_emails,
)
from CTFd.utils.decorators.visibility import check_challenge_visibility
from CTFd.utils.helpers import get_errors, get_infos
from CTFd.utils.user import authed, get_current_team, get_current_user

challenges = Blueprint("challenges", __name__)


def _slugify(value):
    value = (value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _extract_tag_value(challenge, prefixes):
    for tag in challenge.tags:
        raw_value = (tag.value or "").strip()
        if ":" not in raw_value:
            continue
        key, value = raw_value.split(":", 1)
        if key.strip().lower() in prefixes:
            return value.strip()
    return None


def _challenge_difficulty(challenge):
    tagged_difficulty = _extract_tag_value(
        challenge, {"difficulty", "difficulte", "level"}
    )
    if tagged_difficulty:
        return tagged_difficulty

    if challenge.value <= 100:
        return "Facile"
    if challenge.value <= 250:
        return "Intermediaire"
    return "Difficile"


def _room_duration(challenges_for_room):
    for challenge in challenges_for_room:
        tagged_duration = _extract_tag_value(
            challenge, {"duration", "room_duration", "room-duration"}
        )
        if tagged_duration and tagged_duration.isdigit():
            return int(tagged_duration)
    return 30


def _room_description(challenges_for_room):
    for challenge in challenges_for_room:
        tagged_description = _extract_tag_value(
            challenge, {"room_description", "room-description", "description"}
        )
        if tagged_description:
            return tagged_description

    first_with_description = next(
        (c.description for c in challenges_for_room if c.description), None
    )
    if first_with_description:
        clean_text = re.sub(r"<[^>]+>", "", first_with_description).strip()
        if clean_text:
            return clean_text[:260]

    return "Progression guidee challenge par challenge."


def _room_difficulty(challenges_for_room):
    difficulties = [_challenge_difficulty(challenge) for challenge in challenges_for_room]
    if not difficulties:
        return "Intermediaire"

    counts = {}
    for difficulty in difficulties:
        counts[difficulty] = counts.get(difficulty, 0) + 1
    return max(counts, key=counts.get)


@challenges.route("/challenges", methods=["GET"])
@require_complete_profile
@during_ctf_time_only
@require_verified_emails
@check_challenge_visibility
def listing():
    if (
        Configs.challenge_visibility == ChallengeVisibilityTypes.PUBLIC
        and authed() is False
    ):
        pass
    else:
        if is_teams_mode() and get_current_team() is None:
            return redirect(url_for("teams.private", next=request.full_path))

    infos = get_infos()
    errors = get_errors()

    if Configs.challenge_visibility == ChallengeVisibilityTypes.ADMINS:
        infos.append(_l("Challenge Visibility is set to Admins Only"))

    if ctf_started() is False:
        errors.append(_l("%(ctf_name)s has not started yet", ctf_name=Configs.ctf_name))

    if ctf_paused() is True:
        infos.append(_l("%(ctf_name)s is paused", ctf_name=Configs.ctf_name))

    if ctf_ended() is True:
        infos.append(_l("%(ctf_name)s has ended", ctf_name=Configs.ctf_name))

    return render_template("challenges.html", infos=infos, errors=errors)


@challenges.route("/rooms/<room_id>", methods=["GET"])
@require_complete_profile
@during_ctf_time_only
@require_verified_emails
@check_challenge_visibility
def room_detail(room_id):
    if (
        Configs.challenge_visibility == ChallengeVisibilityTypes.PUBLIC
        and authed() is False
    ):
        pass
    else:
        if is_teams_mode() and get_current_team() is None:
            return redirect(url_for("teams.private", next=request.full_path))

    visible_challenges = (
        Challenges.query.filter_by(state="visible")
        .order_by(Challenges.position.asc(), Challenges.id.asc())
        .all()
    )
    if not visible_challenges:
        abort(404)

    room_challenges = [
        c for c in visible_challenges if (c.category or "") == room_id
    ]
    if not room_challenges:
        room_challenges = [
            c for c in visible_challenges if _slugify(c.category) == _slugify(room_id)
        ]

    if not room_challenges:
        abort(404)

    current_user = get_current_user() if authed() else None
    current_team = get_current_team() if authed() else None

    challenge_ids = [challenge.id for challenge in room_challenges]

    solved_ids = set()
    if authed() and is_teams_mode() and current_team:
        solved_ids = {
            challenge_id
            for challenge_id, in Solves.query.with_entities(Solves.challenge_id)
            .filter(
                Solves.challenge_id.in_(challenge_ids),
                Solves.team_id == current_team.id,
            )
            .all()
        }
    elif authed() and current_user:
        solved_ids = {
            challenge_id
            for challenge_id, in Solves.query.with_entities(Solves.challenge_id)
            .filter(
                Solves.challenge_id.in_(challenge_ids),
                Solves.user_id == current_user.id,
            )
            .all()
        }

    if is_teams_mode():
        players_count = (
            Solves.query.with_entities(func.count(func.distinct(Solves.team_id)))
            .filter(
                Solves.challenge_id.in_(challenge_ids),
                Solves.team_id.isnot(None),
            )
            .scalar()
            or 0
        )
    else:
        players_count = (
            Solves.query.with_entities(func.count(func.distinct(Solves.user_id)))
            .filter(
                Solves.challenge_id.in_(challenge_ids),
                Solves.user_id.isnot(None),
            )
            .scalar()
            or 0
        )

    challenge_cards = []
    for challenge in room_challenges:
        challenge_cards.append(
            {
                "id": challenge.id,
                "name": challenge.name,
                "category": challenge.category,
                "value": challenge.value,
                "difficulty": _challenge_difficulty(challenge),
                "solved": challenge.id in solved_ids,
            }
        )

    solved_count = len(solved_ids)
    total_count = len(challenge_cards)
    progress_percent = int((solved_count / total_count) * 100) if total_count else 0

    room = {
        "id": room_id,
        "title": room_challenges[0].category or f"Room {room_id}",
        "description": _room_description(room_challenges),
        "difficulty": _room_difficulty(room_challenges),
        "duration": _room_duration(room_challenges),
        "players_count": players_count,
    }

    return render_template(
        "room_detail.html",
        room=room,
        progress_percent=progress_percent,
        solved_count=solved_count,
        total_count=total_count,
        challenges=challenge_cards,
        challenge_target_ip=current_app.config.get("CHALLENGE_TARGET_IP", "10.10.155.42"),
    )
