import functools

from flask import abort

from CTFd.utils import get_config
from CTFd.utils.modes import TEAMS_MODE, USERS_MODE


def require_team_mode(f):
    @functools.wraps(f)
    def _require_team_mode(*args, **kwargs):
        if get_config("user_mode") == USERS_MODE:
            abort(404)
        return f(*args, **kwargs)

    return _require_team_mode


def require_team_private_page(f):
    """Hub /team : équipe + inscription — disponible en mode teams et users (utilisateurs connectés)."""

    @functools.wraps(f)
    def _require_team_private_page(*args, **kwargs):
        mode = get_config("user_mode")
        if mode in (TEAMS_MODE, USERS_MODE):
            return f(*args, **kwargs)
        abort(404)

    return _require_team_private_page


def require_team_enrollment_enabled(f):
    """Création / join / invite équipe : actif en mode teams et en mode users (hybride équipe)."""

    @functools.wraps(f)
    def _require_team_enrollment_enabled(*args, **kwargs):
        if get_config("user_mode") in (TEAMS_MODE, USERS_MODE):
            return f(*args, **kwargs)
        abort(404)

    return _require_team_enrollment_enabled


def require_user_mode(f):
    @functools.wraps(f)
    def _require_user_mode(*args, **kwargs):
        if get_config("user_mode") == TEAMS_MODE:
            abort(404)
        return f(*args, **kwargs)

    return _require_user_mode
