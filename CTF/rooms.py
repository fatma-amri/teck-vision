"""Room detail views — redirects /play/<slug> to /rooms/<slug> for unified dark theme."""

from flask import Blueprint, redirect, url_for

from CTFd.utils.decorators import authed_only

rooms = Blueprint("rooms", __name__, url_prefix="/play")


@rooms.route("/<room_slug>")
@authed_only
def detail(room_slug):
    return redirect(url_for("challenges.room_detail", room_id=room_slug))
