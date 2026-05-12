"""Admin routes for educate room and challenge management."""

import re

from flask import flash, redirect, render_template, request, url_for

from CTFd.admin import admin
from CTFd.models import RoomChallenge, Rooms, db
from CTFd.utils.decorators import admins_only

EDUCATE_SLUG_PREFIX = "educate-"


def _slugify(value):
    value = (value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _educate_query():
    return Rooms.query.filter(Rooms.slug.like(f"{EDUCATE_SLUG_PREFIX}%"))


@admin.route("/admin/educate/", methods=["GET"])
@admins_only
def educate_listing():
    rooms = _educate_query().order_by(Rooms.id.asc()).all()
    room_data = [{"room": room, "challenge_count": room.challenges.count()} for room in rooms]
    return render_template("admin/educate/list.html", rooms=room_data)


@admin.route("/admin/educate/new", methods=["GET", "POST"])
@admins_only
def educate_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        difficulty = request.form.get("difficulty", "Easy")
        duration = request.form.get("duration", 30)
        target_ip = request.form.get("target_ip", "").strip()
        aws_challenge_id = request.form.get("aws_challenge_id", "").strip()

        if not name:
            flash("Educate name is required.", "error")
            return render_template("admin/educate/new.html")

        slug = f"{EDUCATE_SLUG_PREFIX}{_slugify(name)}"
        if Rooms.query.filter_by(slug=slug).first():
            flash(f"An educate room with slug '{slug}' already exists.", "error")
            return render_template("admin/educate/new.html")

        try:
            duration = int(duration)
        except (ValueError, TypeError):
            duration = 30

        room = Rooms(
            name=name,
            slug=slug,
            description=description,
            difficulty=difficulty,
            duration=duration,
            target_ip=target_ip or None,
            aws_challenge_id=aws_challenge_id or None,
            is_active=True,
        )
        db.session.add(room)
        db.session.commit()
        flash(f"Educate room '{name}' created.", "success")
        return redirect(url_for("admin.educate_listing"))

    return render_template("admin/educate/new.html")


@admin.route("/admin/educate/<int:room_id>/edit", methods=["GET", "POST"])
@admins_only
def educate_edit(room_id):
    room = _educate_query().filter_by(id=room_id).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        difficulty = request.form.get("difficulty", "Easy")
        duration = request.form.get("duration", 30)
        target_ip = request.form.get("target_ip", "").strip()
        aws_challenge_id = request.form.get("aws_challenge_id", "").strip()
        is_active = request.form.get("is_active") == "1"

        if not name:
            flash("Educate name is required.", "error")
            return render_template("admin/educate/edit.html", room=room)

        try:
            duration = int(duration)
        except (ValueError, TypeError):
            duration = 30

        room.name = name
        room.description = description
        room.difficulty = difficulty
        room.duration = duration
        room.target_ip = target_ip or None
        room.aws_challenge_id = aws_challenge_id or None
        room.is_active = is_active
        db.session.commit()
        flash(f"Educate room '{name}' updated.", "success")
        return redirect(url_for("admin.educate_listing"))

    return render_template("admin/educate/edit.html", room=room)


@admin.route("/admin/educate/<int:room_id>/delete", methods=["POST"])
@admins_only
def educate_delete(room_id):
    room = _educate_query().filter_by(id=room_id).first_or_404()
    name = room.name
    db.session.delete(room)
    db.session.commit()
    flash(f"Educate room '{name}' deleted.", "success")
    return redirect(url_for("admin.educate_listing"))


@admin.route("/admin/educate/<int:room_id>/challenges/new", methods=["GET", "POST"])
@admins_only
def educate_challenges_new(room_id):
    room = _educate_query().filter_by(id=room_id).first_or_404()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()
        points = request.form.get("points", 100)
        difficulty = request.form.get("difficulty", "Easy")
        position = request.form.get("position", 0)

        if not title or not answer:
            flash("Title and answer are required.", "error")
            return render_template("admin/educate/challenges/new.html", room=room)
        try:
            points = int(points)
        except (ValueError, TypeError):
            points = 100
        try:
            position = int(position)
        except (ValueError, TypeError):
            position = room.challenges.count()

        db.session.add(
            RoomChallenge(
                room_id=room.id,
                title=title,
                description=description,
                question=question,
                answer=answer,
                points=points,
                difficulty=difficulty,
                position=position,
            )
        )
        db.session.commit()
        flash(f"Challenge '{title}' added.", "success")
        return redirect(url_for("admin.educate_edit", room_id=room.id))

    return render_template(
        "admin/educate/challenges/new.html",
        room=room,
        next_position=room.challenges.count(),
    )


@admin.route("/admin/educate/<int:room_id>/challenges/<int:cid>/edit", methods=["GET", "POST"])
@admins_only
def educate_challenges_edit(room_id, cid):
    room = _educate_query().filter_by(id=room_id).first_or_404()
    challenge = RoomChallenge.query.filter_by(id=cid, room_id=room_id).first_or_404()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        question = request.form.get("question", "").strip()
        answer = request.form.get("answer", "").strip()
        points = request.form.get("points", 100)
        difficulty = request.form.get("difficulty", "Easy")
        position = request.form.get("position", challenge.position)

        if not title or not answer:
            flash("Title and answer are required.", "error")
            return render_template("admin/educate/challenges/edit.html", room=room, challenge=challenge)
        try:
            points = int(points)
        except (ValueError, TypeError):
            points = 100
        try:
            position = int(position)
        except (ValueError, TypeError):
            position = challenge.position

        challenge.title = title
        challenge.description = description
        challenge.question = question
        challenge.answer = answer
        challenge.points = points
        challenge.difficulty = difficulty
        challenge.position = position
        db.session.commit()
        flash(f"Challenge '{title}' updated.", "success")
        return redirect(url_for("admin.educate_edit", room_id=room.id))

    return render_template("admin/educate/challenges/edit.html", room=room, challenge=challenge)


@admin.route("/admin/educate/<int:room_id>/challenges/<int:cid>/delete", methods=["POST"])
@admins_only
def educate_challenges_delete(room_id, cid):
    room = _educate_query().filter_by(id=room_id).first_or_404()
    challenge = RoomChallenge.query.filter_by(id=cid, room_id=room_id).first_or_404()
    title = challenge.title
    db.session.delete(challenge)
    db.session.commit()
    flash(f"Challenge '{title}' deleted.", "success")
    return redirect(url_for("admin.educate_edit", room_id=room.id))

