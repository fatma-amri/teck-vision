import logging
import re

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from flask_babel import lazy_gettext as _l
from sqlalchemy import func

from CTFd.cache import cache
from CTFd.constants.config import ChallengeVisibilityTypes, Configs
from CTFd.models import Challenges, Rooms, Solves
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

logger = logging.getLogger(__name__)

challenges = Blueprint("challenges", __name__)


def _check_rate_limit(key, limit=60, window=60):
    """Simple rate limiting implementation using cache.
    
    Args:
        key: Identifier for rate limiting (e.g., IP address)
        limit: Max requests allowed
        window: Time window in seconds
        
    Returns:
        True if request is allowed, False if rate limited
    """
    cache_key = f"ratelimit_{key}"
    current_count = cache.get(cache_key) or 0
    
    if current_count >= limit:
        return False
    
    cache.set(cache_key, current_count + 1, timeout=window)
    return True


def _slugify(value):
    """Convert string to URL-safe slug format.
    
    Args:
        value: String to convert
        
    Returns:
        Lowercased string with non-alphanumeric characters replaced by hyphens.
    """
    value = (value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _extract_tag_value(challenge, prefixes):
    """Extract value from challenge tags by prefix match.
    
    Searches challenge tags for key-value pairs and returns the value
    if the key matches one of the provided prefixes.
    
    Args:
        challenge: Challenge object with tags attribute
        prefixes: Set of prefix strings to match
        
    Returns:
        Tag value if found, None otherwise.
    """
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
    """Determine the most common difficulty level for a room of challenges.
    
    Args:
        challenges_for_room: List of Challenge objects
        
    Returns:
        The most frequently occurring difficulty level string.
    """
    difficulties = [_challenge_difficulty(challenge) for challenge in challenges_for_room]
    if not difficulties:
        return "Intermediaire"

    counts = {}
    for difficulty in difficulties:
        counts[difficulty] = counts.get(difficulty, 0) + 1
    return max(counts, key=counts.get)


@challenges.route("/rooms/", methods=["GET"])
@require_complete_profile
@during_ctf_time_only
@require_verified_emails
@check_challenge_visibility
def rooms_listing():
    """List all available rooms."""
    if (
        Configs.challenge_visibility == ChallengeVisibilityTypes.PUBLIC
        and authed() is False
    ):
        pass
    else:
        if is_teams_mode() and get_current_team() is None:
            return redirect(url_for("teams.private", next=request.full_path))

    rooms = Rooms.query.all()

    # Build room list enriched with challenge counts and player counts
    room_list = []
    for room in rooms:
        challenges_for_room = (
            Challenges.query.filter_by(category=room.slug, state="visible").all()
        )
        total = len(challenges_for_room)
        challenge_ids = [c.id for c in challenges_for_room]

        if is_teams_mode():
            players = (
                Solves.query.with_entities(func.count(func.distinct(Solves.team_id)))
                .filter(
                    Solves.challenge_id.in_(challenge_ids),
                    Solves.team_id.isnot(None),
                )
                .scalar()
                or 0
            )
        else:
            players = (
                Solves.query.with_entities(func.count(func.distinct(Solves.user_id)))
                .filter(
                    Solves.challenge_id.in_(challenge_ids),
                    Solves.user_id.isnot(None),
                )
                .scalar()
                or 0
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
                "players_count": players,
            }
        )

    return render_template("rooms.html", rooms=room_list)


@challenges.route("/challenges", methods=["GET"])
@require_complete_profile
@during_ctf_time_only
@require_verified_emails
@check_challenge_visibility
def listing():
    """Display list of available challenges to the user.
    
    Returns challenges based on visibility settings and user authentication status.
    Enforces team mode requirements and shows relevant status messages.
    """
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
    # Rate limiting: max 60 requests per minute per IP
    client_ip = request.remote_addr
    if not _check_rate_limit(client_ip, limit=60, window=60):
        abort(429)  # Too Many Requests
    
    # Log room access for security audit trail
    user = get_current_user() if authed() else None
    team = get_current_team() if authed() else None
    logger.info(
        f"Room access: room_id={room_id}, user_id={user.id if user else None}, "
        f"team_id={team.id if team else None}, ip={client_ip}"
    )
    
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
    
    # If no visible challenges exist, show appropriate message based on context
    if not visible_challenges:
        if Challenges.query.count() == 0:
            return render_template(
                "error.html",
                status=404,
                message=_l("No challenges configured yet")
            )
        elif ctf_started() is False:
            return render_template(
                "error.html",
                status=503,
                message=_l("%(ctf_name)s has not started yet", ctf_name=Configs.ctf_name)
            )
        else:
            return render_template(
                "error.html",
                status=403,
                message=_l("Challenges are not yet visible")
            )

    # Try exact match first
    room_challenges = [
        c for c in visible_challenges if (c.category or "") == room_id
    ]
    
    # If no exact match, find by slug and enforce canonical URL
    if not room_challenges:
        for challenge in visible_challenges:
            if _slugify(challenge.category) == _slugify(room_id):
                room_challenges.append(challenge)
        
        # Redirect to canonical slug if found but URL doesn't match
        if room_challenges:
            canonical_slug = _slugify(room_challenges[0].category)
            if room_id != canonical_slug:
                return redirect(url_for(".room_detail", room_id=canonical_slug))

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

    # Cache player count for 30 seconds to reduce database load
    cache_key = f"room_players_count_{','.join(map(str, sorted(challenge_ids)))}"
    players_count = cache.get(cache_key)
    
    if players_count is None:
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
        cache.set(cache_key, players_count, timeout=30)

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

    # Look up Room model for target_ip (fallback to config)
    room_model = Rooms.query.filter_by(slug=_slugify(room.get("id", ""))).first()
    target_ip = (
        room_model.target_ip
        if room_model and room_model.target_ip
        else current_app.config.get("CHALLENGE_TARGET_IP", "15.237.60.47")
    )

    return render_template(
        "room_detail.html",
        room=room,
        room_slug=_slugify(room.get("id", "")),
        progress_percent=progress_percent,
        solved_count=solved_count,
        total_count=total_count,
        challenges=challenge_cards,
        challenge_target_ip=target_ip,
    )
