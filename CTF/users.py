from flask import Blueprint, abort, redirect, render_template, request, url_for

from CTFd.models import Users
from CTFd.utils import config, get_config
from CTFd.utils.decorators import authed_only
from CTFd.utils.decorators.visibility import (
    check_account_visibility,
    check_score_visibility,
)
from CTFd.utils.helpers import get_errors, get_infos
from CTFd.utils.modes import USERS_MODE
from CTFd.utils.user import authed, get_current_user, is_admin

users = Blueprint("users", __name__)


@users.route("/users")
@authed_only
@check_account_visibility
def listing():
    if get_config("user_mode") == USERS_MODE and not is_admin():
        abort(
            403,
            description="The full operator directory is only available to administrators.",
        )

    q = request.args.get("q")
    field = request.args.get("field", "name")
    if field not in ("name", "affiliation", "website"):
        field = "name"

    filters = []
    if q:
        filters.append(getattr(Users, field).like("%{}%".format(q)))

    users_paginated = (
        Users.query.filter_by(banned=False, hidden=False)
        .filter(*filters)
        .order_by(Users.id.asc())
        .paginate(per_page=50, error_out=False)
    )

    args = dict(request.args)
    args.pop("page", 1)

    return render_template(
        "users/users.html",
        users=users_paginated,
        prev_page=url_for(request.endpoint, page=users_paginated.prev_num, **args),
        next_page=url_for(request.endpoint, page=users_paginated.next_num, **args),
        q=q,
        field=field,
    )


@users.route("/users/team")
@authed_only
def team_roster():
    user = get_current_user()
    if not user.team_id:
        return redirect(url_for("teams.private"))

    team = user.team
    if team is None:
        return redirect(url_for("teams.private"))

    teammates = (
        Users.query.filter_by(team_id=user.team_id, banned=False, hidden=False)
        .order_by(Users.name.asc())
        .all()
    )

    return render_template(
        "users/users_teammates.html",
        teammates=teammates,
        team=team,
    )


@users.route("/profile")
@users.route("/user")
@authed_only
def private():
    infos = get_infos()
    errors = get_errors()

    user = get_current_user()

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    return render_template(
        "users/private.html",
        user=user,
        account=user.account,
        user_score=user.get_score(admin=True),
        infos=infos,
        errors=errors,
    )


@users.route("/users/<int:user_id>")
@authed_only
@check_account_visibility
@check_score_visibility
def public(user_id):
    infos = get_infos()
    errors = get_errors()
    user = Users.query.filter_by(id=user_id, banned=False, hidden=False).first_or_404()

    if get_config("user_mode") == USERS_MODE:
        if is_admin():
            pass
        elif authed():
            viewer = get_current_user()
            if viewer.id != user_id and (
                not viewer.team_id or viewer.team_id != user.team_id
            ):
                abort(
                    403,
                    description="You can only view profiles of operators on your team.",
                )
        else:
            abort(403)

    if config.is_scoreboard_frozen():
        infos.append("Scoreboard has been frozen")

    return render_template(
        "users/public.html", user=user, account=user.account,
        user_score=user.get_score(admin=False),
        infos=infos, errors=errors,
    )
