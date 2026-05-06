"""Admin routes for room and room-challenge management."""

import json
import re
import uuid

import requests
from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from CTFd.admin import admin
from CTFd.models import Challenges, RoomChallenge, Rooms, db
from CTFd.utils.decorators import admins_only

OVA_UPLOAD_API_URL = (
    "https://5b5s89lx86.execute-api.eu-west-3.amazonaws.com/dev/UploadFileAPI"
)


def _slugify(value):
    value = (value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _extract_upload_location(response_json, fallback_name):
    if not isinstance(response_json, dict):
        return fallback_name
    for key in ("url", "file_url", "fileUrl", "location", "Location"):
        if response_json.get(key):
            return response_json[key]
    for key in ("key", "file_key", "fileKey", "filename", "fileName"):
        if response_json.get(key):
            return response_json[key]
    data = response_json.get("data")
    if isinstance(data, dict):
        return _extract_upload_location(data, fallback_name)
    body = response_json.get("body")
    if isinstance(body, dict):
        return _extract_upload_location(body, fallback_name)
    if isinstance(body, str) and body.strip():
        try:
            return _extract_upload_location(json.loads(body), fallback_name)
        except ValueError:
            return body.strip()
    return fallback_name


def _upload_ova_file(file_storage, slug):
    filename = secure_filename(file_storage.filename or "")
    if not filename.lower().endswith(".ova"):
        raise ValueError("Only .ova files are allowed.")
    unique_name = f"{slug}-{uuid.uuid4().hex[:8]}.ova"
    upload_url = current_app.config.get("OVA_UPLOAD_API_URL", OVA_UPLOAD_API_URL)
    file_storage.stream.seek(0)
    try:
        response = requests.post(
            upload_url,
            files={"file": (unique_name, file_storage.stream, file_storage.mimetype or "application/octet-stream")},
            data={"filename": unique_name},
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise ValueError(f"OVA upload failed: {e}") from e
    try:
        response_json = response.json()
    except ValueError:
        return response.text.strip() or unique_name
    return _extract_upload_location(response_json, unique_name)


# ── Create CTF (room + flags + OVA in one form) ───────────────────────────────

@admin.route("/admin/create-ctf", methods=["GET", "POST"])
@admins_only
def create_ctf():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        difficulty = request.form.get("difficulty", "Easy")
        duration = request.form.get("duration", 30)
        target_ip = request.form.get("target_ip", "").strip() or None
        ova_file = request.files.get("ova_image")
        ova_location = request.form.get("ova_location", "").strip()

        titles = request.form.getlist("flag_title[]")
        questions = request.form.getlist("flag_question[]")
        answers = request.form.getlist("flag_answer[]")
        points_values = request.form.getlist("flag_points[]")

        if not name:
            flash("CTF name is required.", "error")
            return render_template("admin/create_ctf.html")

        flag_rows = []
        for i, answer in enumerate(answers):
            answer = (answer or "").strip()
            if not answer:
                continue
            title = titles[i].strip() if i < len(titles) else ""
            question = questions[i].strip() if i < len(questions) else ""
            try:
                pts = int(points_values[i]) if i < len(points_values) else 100
            except (ValueError, TypeError):
                pts = 100
            flag_rows.append({
                "title": title or f"Flag {len(flag_rows) + 1}",
                "question": question,
                "answer": answer,
                "points": pts,
                "position": len(flag_rows),
            })

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

        if ova_file and ova_file.filename and not ova_location:
            try:
                ova_location = _upload_ova_file(ova_file, slug)
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
            target_ip=target_ip,
            is_active=True,
        )
        db.session.add(room)
        db.session.flush()

        for row in flag_rows:
            db.session.add(RoomChallenge(
                room_id=room.id,
                title=row["title"],
                description="",
                question=row["question"],
                answer=row["answer"],
                points=row["points"],
                difficulty=difficulty,
                position=row["position"],
            ))

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


# ── Create room (redirect to unified Create CTF flow) ─────────────────────────

@admin.route("/admin/rooms/new", methods=["GET", "POST"])
@admins_only
def rooms_new():
    return redirect(url_for("admin.create_ctf"))


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

        if name != room.name:
            new_slug = _slugify(name)
            conflict = Rooms.query.filter(
                Rooms.slug == new_slug, Rooms.id != room.id
            ).first()
            if conflict:
                flash(
                    f"A room with slug '{new_slug}' already exists — slug not updated.",
                    "warning",
                )
            else:
                room.slug = new_slug

        room.name = name
        room.description = description
        room.difficulty = difficulty
        room.duration = duration
        room.target_ip = target_ip or None
        room.is_active = is_active
        db.session.commit()
        flash(f"Room '{name}' updated.", "success")
        return redirect(url_for("admin.rooms_listing"))

    linked = Challenges.query.filter_by(room_id=room.id).order_by(Challenges.id.asc()).all()
    available = Challenges.query.filter_by(room_id=None).order_by(Challenges.name.asc()).all()
    return render_template("admin/rooms/edit.html", room=room, linked_challenges=linked, available_challenges=available)


# ── Link / unlink standard challenges to a room ───────────────────────────────

@admin.route("/admin/rooms/<int:room_id>/link-challenge", methods=["POST"])
@admins_only
def room_link_challenge(room_id):
    room = Rooms.query.get_or_404(room_id)
    challenge_id = request.form.get("challenge_id", type=int)
    challenge = Challenges.query.get_or_404(challenge_id)
    challenge.room_id = room.id
    db.session.commit()
    flash(f"Challenge '{challenge.name}' linked to room '{room.name}'.", "success")
    return redirect(url_for("admin.rooms_edit", room_id=room.id))


@admin.route("/admin/rooms/<int:room_id>/unlink-challenge/<int:challenge_id>", methods=["POST"])
@admins_only
def room_unlink_challenge(room_id, challenge_id):
    room = Rooms.query.get_or_404(room_id)
    challenge = Challenges.query.filter_by(id=challenge_id, room_id=room.id).first_or_404()
    challenge.room_id = None
    db.session.commit()
    flash(f"Challenge '{challenge.name}' unlinked.", "success")
    return redirect(url_for("admin.rooms_edit", room_id=room.id))


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
