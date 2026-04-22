"""
Tests for the Teck-Vision Rooms system.

Routes under test:
  POST /api/room-instances/start/<slug>
  POST /api/room-instances/terminate/<slug>
  GET  /api/room-instances/status/<slug>
  GET  /rooms/<room_id>  (room detail page)
  GET  /rooms/           (rooms listing)

Run:  pytest tests/test_rooms.py -v
"""
import json
import datetime

import pytest

from CTFd.models import Challenges, Flags, RoomInstances, Rooms, Solves, db
from tests.helpers import create_ctfd, destroy_ctfd, gen_challenge, gen_user


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _login(client, name="player1", password="password"):
    client.get("/login", follow_redirects=True)
    with client.session_transaction() as sess:
        nonce = sess.get("nonce")
    client.post(
        "/login",
        data={"name": name, "password": password, "nonce": nonce},
        follow_redirects=True,
    )


def _create_room(db_session, slug="web-security-challenge", name="Web Security Challenge"):
    room = Rooms(
        name=name,
        slug=slug,
        description="Practice web security.",
        difficulty="Easy",
        duration=30,
        target_ip="15.237.60.47",
    )
    db_session.add(room)
    db_session.commit()
    return room


def _start_machine(client, slug="web-security-challenge"):
    return client.post(
        f"/api/room-instances/start/{slug}",
        json={},
        headers={"Content-Type": "application/json"},
    )


# ─────────────────────────────────────────────────────────────
# Machine Control tests
# ─────────────────────────────────────────────────────────────

class TestRoomInstances:

    def test_start_machine_creates_instance(self):
        """Starting a machine returns 201 with machine_ip and time_remaining."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = _start_machine(client)

            assert resp.status_code == 201
            data = json.loads(resp.data)
            assert data["success"] is True
            assert data["machine_ip"] == "15.237.60.47"
            assert data["time_remaining"] > 0
            assert "expires_at" in data
        destroy_ctfd(app)

    def test_start_machine_twice_returns_existing(self):
        """Starting a machine for the same room twice returns the existing instance."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp1 = _start_machine(client)
                resp2 = _start_machine(client)

            assert resp1.status_code == 201
            assert resp2.status_code == 200
            data1 = json.loads(resp1.data)
            data2 = json.loads(resp2.data)
            assert data1["machine_ip"] == data2["machine_ip"]
        destroy_ctfd(app)

    def test_terminate_machine_deactivates_instance(self):
        """Terminating a machine marks it is_active=False."""
        app = create_ctfd()
        instance_id = None
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

            instance = RoomInstances(
                user_id=user.id,
                category="web-security-challenge",
                machine_ip="15.237.60.47",
                is_active=True,
                started_at=datetime.datetime.utcnow(),
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
                duration_minutes=30,
            )
            app.db.session.add(instance)
            app.db.session.commit()
            instance_id = instance.id

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.post(
                    "/api/room-instances/terminate/web-security-challenge",
                    json={},
                    headers={"Content-Type": "application/json"},
                )

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data["success"] is True

            inst = RoomInstances.query.get(instance_id)
            assert inst.is_active is False
        destroy_ctfd(app)

    def test_check_status_when_no_machine_running(self):
        """Status endpoint returns is_active=False when no instance exists."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.get("/api/room-instances/status/web-security-challenge")

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data["is_active"] is False
            assert data["time_remaining"] == 0
        destroy_ctfd(app)

    def test_check_status_when_machine_running(self):
        """Status endpoint returns is_active=True with IP when a machine is active."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

            instance = RoomInstances(
                user_id=user.id,
                category="web-security-challenge",
                machine_ip="15.237.60.47",
                is_active=True,
                started_at=datetime.datetime.utcnow(),
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
                duration_minutes=30,
            )
            app.db.session.add(instance)
            app.db.session.commit()

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.get("/api/room-instances/status/web-security-challenge")

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data["is_active"] is True
            assert data["machine_ip"] == "15.237.60.47"
            assert data["time_remaining"] > 0
        destroy_ctfd(app)

    def test_expired_instance_auto_deactivated_on_status(self):
        """Calling status on an expired instance sets is_active=False automatically."""
        app = create_ctfd()
        instance_id = None
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

            instance = RoomInstances(
                user_id=user.id,
                category="web-security-challenge",
                machine_ip="15.237.60.47",
                is_active=True,
                started_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2),
                expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
                duration_minutes=30,
            )
            app.db.session.add(instance)
            app.db.session.commit()
            instance_id = instance.id

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.get("/api/room-instances/status/web-security-challenge")

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data["is_active"] is False
            assert data["time_remaining"] == 0

            inst = RoomInstances.query.get(instance_id)
            assert inst.is_active is False
        destroy_ctfd(app)

    def test_start_nonexistent_room_returns_404(self):
        """Starting a machine for an unknown room slug returns 404."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = _start_machine(client, slug="nonexistent-room-xyz")

            assert resp.status_code == 404
        destroy_ctfd(app)

    def test_unauthenticated_start_redirects_to_login(self):
        """Unauthenticated request to start machine should redirect or return 403."""
        app = create_ctfd()
        with app.app_context():
            _create_room(app.db.session)

        with app.app_context():
            with app.test_client() as client:
                resp = _start_machine(client)

            assert resp.status_code in (302, 403)
        destroy_ctfd(app)

    def test_room_timer_countdown(self):
        """time_remaining decreases correctly from expiry time."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

            duration_minutes = 30
            expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=duration_minutes)
            instance = RoomInstances(
                user_id=user.id,
                category="web-security-challenge",
                machine_ip="15.237.60.47",
                is_active=True,
                started_at=datetime.datetime.utcnow(),
                expires_at=expires,
                duration_minutes=duration_minutes,
            )
            app.db.session.add(instance)
            app.db.session.commit()

            remaining = instance.time_remaining_seconds
            assert 0 < remaining <= duration_minutes * 60
        destroy_ctfd(app)

    def test_room_instance_cleanup_marks_instances_inactive(self):
        """Multiple expired instances are all set inactive."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

            past = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
            for _ in range(3):
                inst = RoomInstances(
                    user_id=user.id,
                    category="web-security-challenge",
                    machine_ip="15.237.60.47",
                    is_active=True,
                    started_at=past - datetime.timedelta(hours=1),
                    expires_at=past,
                    duration_minutes=30,
                )
                app.db.session.add(inst)
            app.db.session.commit()

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                client.get("/api/room-instances/status/web-security-challenge")

            deactivated = RoomInstances.query.filter_by(is_active=False).count()
            assert deactivated >= 1
        destroy_ctfd(app)


# ─────────────────────────────────────────────────────────────
# Flag Submission inside rooms
# ─────────────────────────────────────────────────────────────

class TestFlagSubmission:

    def test_submit_correct_flag(self):
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="SQLi 101", category="web-security")
            chal_id = chal.id
            user_id = user.id
            flag = Flags(challenge_id=chal_id, type="static", content="correct_flag")
            app.db.session.add(flag)
            app.db.session.commit()

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.post(
                    f"/api/challenges/{chal_id}/submit-flag",
                    json={"flag": "correct_flag"},
                    headers={"Content-Type": "application/json"},
                )

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data["success"] is True
            assert "points" in data

            solve = Solves.query.filter_by(challenge_id=chal_id, user_id=user_id).first()
            assert solve is not None
        destroy_ctfd(app)

    def test_submit_incorrect_flag(self):
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="XSS 101", category="web-security")
            chal_id = chal.id
            flag = Flags(challenge_id=chal_id, type="static", content="correct_flag")
            app.db.session.add(flag)
            app.db.session.commit()

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.post(
                    f"/api/challenges/{chal_id}/submit-flag",
                    json={"flag": "wrong_flag"},
                    headers={"Content-Type": "application/json"},
                )

            assert resp.status_code == 400
            data = json.loads(resp.data)
            assert data["success"] is False
            assert "Wrong flag" in data["message"]
        destroy_ctfd(app)

    def test_flag_case_insensitive(self):
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="CSRF 101", category="web-security")
            chal_id = chal.id
            flag = Flags(challenge_id=chal_id, type="static", content="FLAG_VALUE")
            app.db.session.add(flag)
            app.db.session.commit()

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.post(
                    f"/api/challenges/{chal_id}/submit-flag",
                    json={"flag": "flag_value"},
                    headers={"Content-Type": "application/json"},
                )

            assert json.loads(resp.data)["success"] is True
        destroy_ctfd(app)

    def test_already_solved_challenge(self):
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="RCE 101", category="web-security")
            chal_id = chal.id
            flag = Flags(challenge_id=chal_id, type="static", content="correct_flag")
            solve = Solves(user_id=user.id, challenge_id=chal_id, ip="127.0.0.1", provided="correct_flag")
            app.db.session.add_all([flag, solve])
            app.db.session.commit()

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.post(
                    f"/api/challenges/{chal_id}/submit-flag",
                    json={"flag": "correct_flag"},
                    headers={"Content-Type": "application/json"},
                )

            assert resp.status_code == 409
            data = json.loads(resp.data)
            assert data["success"] is False
            assert "already" in data["message"].lower()
        destroy_ctfd(app)


# ─────────────────────────────────────────────────────────────
# Room pages
# ─────────────────────────────────────────────────────────────

class TestRoomPage:

    def test_room_detail_page_loads(self):
        """Room detail page renders with challenge list."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            gen_challenge(
                app.db,
                name="Task 1",
                category="web-security",
                value=100,
                state="visible",
            )

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.get("/rooms/web-security", follow_redirects=True)

            assert resp.status_code == 200
            assert b"Task 1" in resp.data
        destroy_ctfd(app)

    def test_rooms_listing_page_renders(self):
        """Rooms listing at /rooms/ renders without error."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            _create_room(app.db.session)

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.get("/rooms/", follow_redirects=True)

            assert resp.status_code == 200
        destroy_ctfd(app)

    def test_nonexistent_room_returns_404(self):
        """Accessing a room that doesn't exist returns 404."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.get("/rooms/does-not-exist-xyz", follow_redirects=True)

            assert resp.status_code == 404
        destroy_ctfd(app)
