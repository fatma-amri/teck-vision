"""Admin routes for room and room-challenge management."""

import os
import re
import uuid

from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from CTFd.admin import admin
from CTFd.models import RoomChallenge, Rooms, db
from CTFd.utils.decorators import admins_only


def _slugify(value):
    value = (value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _save_ova_file(file_storage, slug):
    filename = secure_filename(file_storage.filename or "")
    if not filename.lower().endswith(".ova"):
        raise ValueError("Only .ova files are allowed.")

    upload_root = current_app.config.get("UPLOAD_FOLDER")
    ova_dir = os.path.join(upload_root, "ctf_ovas")
    os.makedirs(ova_dir, exist_ok=True)

    unique_name = f"{slug}-{uuid.uuid4().hex[:8]}.ova"
    full_path = os.path.join(ova_dir, unique_name)
    file_storage.save(full_path)
    return os.path.join("ctf_ovas", unique_name).replace("\\", "/")


@admin.route("/admin/create-ctf", methods=["GET", "POST"])
@admins_only
def create_ctf():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        difficulty = request.form.get("difficulty", "Easy")
        duration = request.form.get("duration", 30)
        ova_file = request.files.get("ova_image")

        titles = request.form.getlist("flag_title[]")
        questions = request.form.getlist("flag_question[]")
        answers = request.form.getlist("flag_answer[]")
        points_values = request.form.getlist("flag_points[]")

        if not name:
            flash("CTF name is required.", "error")
            return render_template("admin/create_ctf.html")

        if not ova_file or not ova_file.filename:
            flash("Drop Your OVA Image is required.", "error")
            return render_template("admin/create_ctf.html")

        flag_rows = []
        for index, answer in enumerate(answers):
            answer = (answer or "").strip()
            if not answer:
                continue
            title = titles[index].strip() if index < len(titles) else ""
            question = questions[index].strip() if index < len(questions) else ""
            points = points_values[index] if index < len(points_values) else 100
            try:
                points = int(points)
            except (ValueError, TypeError):
                points = 100
            flag_rows.append(
                {
                    "title": title or f"Flag {len(flag_rows) + 1}",
                    "question": question,
                    "answer": answer,
                    "points": points,
                    "position": len(flag_rows),
                }
            )

        if not flag_rows:
            flash("Add at least one flag.", "error")
            return render_template("admin/create_ctf.html")

        slug = _slugify(name)
        if Rooms.query.filter_by(slug=slug).first():
            flash(f"A CTF with slug '{slug}' already exists.", "error")
            return render_template("admin/create_ctf.html")

        try:
            duration = int(duration)
        except (ValueError, TypeError):
            duration = 30

        try:
            ova_location = _save_ova_file(ova_file, slug)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("admin/create_ctf.html")

        room_description = description
        if ova_location:
            room_description = f"{description}\n\nOVA Image: {ova_location}".strip()

        room = Rooms(
            name=name,
            slug=slug,
            description=room_description,
            difficulty=difficulty,
            duration=duration,
            target_ip="15.237.60.47",
            is_active=True,
        )
        db.session.add(room)
        db.session.flush()

        for row in flag_rows:
            db.session.add(
                RoomChallenge(
                    room_id=room.id,
                    title=row["title"],
                    description="",
                    question=row["question"],
                    answer=row["answer"],
                    points=row["points"],
                    difficulty=difficulty,
                    position=row["position"],
                )
            )

        db.session.commit()
        flash(f"CTF '{name}' created with {len(flag_rows)} flags.", "success")
        return redirect(url_for("admin.rooms_edit", room_id=room.id))

    return render_template("admin/create_ctf.html")


# ── Rooms listing ────────────────────────────────────────────────────────────

@admin.route("/admin/rooms/", methods=["GET"])
@admins_only
def rooms_listing():
    rooms = Rooms.query.order_by(Rooms.id.asc()).all()
    room_data = []
    for room in rooms:
        room_data.append({
            "room": room,
            "challenge_count": room.challenges.count(),
        })
    return render_template("admin/rooms/list.html", rooms=room_data)


# ── Create room ───────────────────────────────────────────────────────────────

@admin.route("/admin/rooms/new", methods=["GET", "POST"])
@admins_only
def rooms_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        difficulty = request.form.get("difficulty", "Easy")
        duration = request.form.get("duration", 30)
        target_ip = request.form.get("target_ip", "").strip()

        if not name:
            flash("Room name is required.", "error")
            return render_template("admin/rooms/new.html")

        slug = _slugify(name)
        if Rooms.query.filter_by(slug=slug).first():
            flash(f"A room with slug '{slug}' already exists.", "error")
            return render_template("admin/rooms/new.html")

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
            target_ip=target_ip or "15.237.60.47",
            is_active=True,
        )
        db.session.add(room)
        db.session.commit()
        flash(f"Room '{name}' created.", "success")
        return redirect(url_for("admin.rooms_listing"))

    return render_template("admin/rooms/new.html")


# ── Edit room ─────────────────────────────────────────────────────────────────

@admin.route("/admin/rooms/<int:room_id>/edit", methods=["GET", "POST"])
@admins_only
def rooms_edit(room_id):
    room = Rooms.query.get_or_404(room_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        difficulty = request.form.get("difficulty", "Easy")
        duration = request.form.get("duration", 30)
        target_ip = request.form.get("target_ip", "").strip()
        is_active = request.form.get("is_active") == "1"

        if not name:
            flash("Room name is required.", "error")
            return render_template("admin/rooms/edit.html", room=room)

        try:
            duration = int(duration)
        except (ValueError, TypeError):
            duration = 30

        room.name = name
        room.description = description
        room.difficulty = difficulty
        room.duration = duration
        room.target_ip = target_ip or "15.237.60.47"
        room.is_active = is_active
        db.session.commit()
        flash(f"Room '{name}' updated.", "success")
        return redirect(url_for("admin.rooms_listing"))

    return render_template("admin/rooms/edit.html", room=room)


# ── Delete room ───────────────────────────────────────────────────────────────

@admin.route("/admin/rooms/<int:room_id>/delete", methods=["POST"])
@admins_only
def rooms_delete(room_id):
    room = Rooms.query.get_or_404(room_id)
    name = room.name
    db.session.delete(room)
    db.session.commit()
    flash(f"Room '{name}' deleted.", "success")
    return redirect(url_for("admin.rooms_listing"))


# ── Add challenge ─────────────────────────────────────────────────────────────

@admin.route("/admin/rooms/<int:room_id>/challenges/new", methods=["GET", "POST"])
@admins_only
def room_challenges_new(room_id):
    room = Rooms.query.get_or_404(room_id)

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
            return render_template("admin/rooms/challenges/new.html", room=room)

        try:
            points = int(points)
        except (ValueError, TypeError):
            points = 100

        try:
            position = int(position)
        except (ValueError, TypeError):
            position = room.challenges.count()

        challenge = RoomChallenge(
            room_id=room.id,
            title=title,
            description=description,
            question=question,
            answer=answer,
            points=points,
            difficulty=difficulty,
            position=position,
        )
        db.session.add(challenge)
        db.session.commit()
        flash(f"Challenge '{title}' added.", "success")
        return redirect(url_for("admin.rooms_edit", room_id=room.id))

    next_position = room.challenges.count()
    return render_template(
        "admin/rooms/challenges/new.html", room=room, next_position=next_position
    )


# ── Edit challenge ────────────────────────────────────────────────────────────

@admin.route(
    "/admin/rooms/<int:room_id>/challenges/<int:cid>/edit", methods=["GET", "POST"]
)
@admins_only
def room_challenges_edit(room_id, cid):
    room = Rooms.query.get_or_404(room_id)
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
            return render_template(
                "admin/rooms/challenges/edit.html", room=room, challenge=challenge
            )

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
        return redirect(url_for("admin.rooms_edit", room_id=room.id))

    return render_template(
        "admin/rooms/challenges/edit.html", room=room, challenge=challenge
    )


# ── Delete challenge ──────────────────────────────────────────────────────────

@admin.route(
    "/admin/rooms/<int:room_id>/challenges/<int:cid>/delete", methods=["POST"]
)
@admins_only
def room_challenges_delete(room_id, cid):
    room = Rooms.query.get_or_404(room_id)
    challenge = RoomChallenge.query.filter_by(id=cid, room_id=room_id).first_or_404()
    title = challenge.title
    db.session.delete(challenge)
    db.session.commit()
    flash(f"Challenge '{title}' deleted.", "success")
    return redirect(url_for("admin.rooms_edit", room_id=room.id))
