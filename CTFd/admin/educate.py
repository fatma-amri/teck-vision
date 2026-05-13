"""Admin routes for educate room and challenge management."""

import os
import re
import uuid

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import BotoCoreError, ClientError
from flask import flash, redirect, render_template, request, url_for
from flask import current_app
from werkzeug.utils import secure_filename

from CTFd.admin import admin
from CTFd.models import RoomChallenge, Rooms, db
from CTFd.utils import get_app_config
from CTFd.utils.decorators import admins_only

EDUCATE_SLUG_PREFIX = "educate-"
EDUCATE_OVA_S3_BUCKET = "ctf-tekup-educate"
EDUCATE_OVA_S3_PREFIX = "educate_ovas"
EDUCATE_OVA_S3_REGION = "eu-west-3"


def _slugify(value):
    value = (value or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def _educate_query():
    return Rooms.query.filter(Rooms.slug.like(f"{EDUCATE_SLUG_PREFIX}%"))


def _get_upload_config(name, default=None):
    return (
        current_app.config.get(name)
        or get_app_config(name)
        or os.environ.get(name)
        or default
    )


def _get_s3_client():
    client_kwargs = {
        "region_name": EDUCATE_OVA_S3_REGION,
    }
    endpoint_url = _get_upload_config("AWS_S3_ENDPOINT_URL")
    if endpoint_url:
        client_kwargs["endpoint_url"] = endpoint_url
    access_key = _get_upload_config("AWS_ACCESS_KEY_ID")
    secret_key = _get_upload_config("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        client_kwargs["aws_access_key_id"] = access_key
        client_kwargs["aws_secret_access_key"] = secret_key
    return boto3.client("s3", **client_kwargs)


def _upload_ova_file(file_storage, slug):
    filename = secure_filename(file_storage.filename or "")
    if not filename.lower().endswith(".ova"):
        raise ValueError("Only .ova files are allowed.")

    # Educate uploads must always go to the dedicated educate bucket.
    bucket = EDUCATE_OVA_S3_BUCKET
    if not bucket:
        raise ValueError("Educate OVA S3 bucket is not configured.")

    prefix = EDUCATE_OVA_S3_PREFIX.strip("/")
    unique_name = f"{slug}-{uuid.uuid4().hex[:8]}-{filename}"
    key = f"{prefix}/{unique_name}" if prefix else unique_name
    file_storage.stream.seek(0)
    try:
        _get_s3_client().upload_fileobj(
            file_storage.stream,
            bucket,
            key,
            ExtraArgs={"ContentType": file_storage.mimetype or "application/octet-stream"},
            Config=TransferConfig(
                multipart_threshold=8 * 1024 * 1024,
                multipart_chunksize=8 * 1024 * 1024,
                max_concurrency=4,
                use_threads=True,
            ),
        )
    except (BotoCoreError, ClientError) as exc:
        raise ValueError(f"Educate OVA upload failed: {exc}") from exc

    return f"s3://{bucket}/{key}"


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
        ova_file = request.files.get("ova_image")
        ova_location = request.form.get("ova_location", "").strip()

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

        if not ova_location and ova_file and ova_file.filename:
            try:
                ova_location = _upload_ova_file(ova_file, slug)
            except ValueError as e:
                flash(str(e), "error")
                return render_template("admin/educate/new.html")

        full_description = description
        if ova_location:
            full_description = f"{description}\n\nOVA Image: {ova_location}".strip()

        room = Rooms(
            name=name,
            slug=slug,
            description=full_description,
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
        ova_file = request.files.get("ova_image")
        ova_location = request.form.get("ova_location", "").strip()

        if not name:
            flash("Educate name is required.", "error")
            return render_template("admin/educate/edit.html", room=room)

        try:
            duration = int(duration)
        except (ValueError, TypeError):
            duration = 30

        if not ova_location and ova_file and ova_file.filename:
            try:
                ova_location = _upload_ova_file(ova_file, room.slug)
            except ValueError as e:
                flash(str(e), "error")
                return render_template("admin/educate/edit.html", room=room)

        full_description = description
        if ova_location:
            full_description = f"{description}\n\nOVA Image: {ova_location}".strip()

        room.name = name
        room.description = full_description
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

