"""
Tests for the Teck-Vision challenges API endpoints.

Routes under test:
  POST /api/challenges/<id>/attempt
  POST /api/challenges/<id>/submit-flag
"""
import json

import pytest

from CTFd.models import Flags, Solves
from tests.helpers import create_ctfd, destroy_ctfd, gen_challenge, gen_flag, gen_user


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


def _submit(client, challenge_id, flag, route="submit-flag"):
    return client.post(
        f"/api/challenges/{challenge_id}/{route}",
        json={"flag": flag},
        headers={"Content-Type": "application/json"},
    )


# ─────────────────────────────────────────────────────────────
# Flag Submission tests
# ─────────────────────────────────────────────────────────────

class TestFlagSubmission:
    """Tests for POST /api/challenges/<id>/submit-flag"""

    def test_correct_flag_returns_success(self):
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="Web 101", category="Web")
            chal_id = chal.id
            chal_value = chal.value
            gen_flag(app.db, chal_id, content="CTF{test_flag}")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = _submit(client, chal_id, "CTF{test_flag}")

            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data["success"] is True
            assert "Correct" in data["message"]
            assert data["points"] == chal_value
        destroy_ctfd(app)

    def test_wrong_flag_returns_400(self):
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="Crypto 101", category="Crypto")
            chal_id = chal.id
            gen_flag(app.db, chal_id, content="CTF{correct}")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = _submit(client, chal_id, "CTF{wrong}")

            assert resp.status_code == 400
            data = json.loads(resp.data)
            assert data["success"] is False
        destroy_ctfd(app)

    def test_flag_matching_is_case_insensitive(self):
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="Misc 101", category="Misc")
            chal_id = chal.id
            gen_flag(app.db, chal_id, content="FLAG_VALUE")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = _submit(client, chal_id, "flag_value")

            assert resp.status_code == 200
            assert json.loads(resp.data)["success"] is True
        destroy_ctfd(app)

    def test_already_solved_returns_409(self):
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="Pwn 101", category="Pwn")
            chal_id = chal.id
            gen_flag(app.db, chal_id, content="CTF{flag}")

            solve = Solves(
                user_id=user.id,
                challenge_id=chal_id,
                ip="127.0.0.1",
                provided="CTF{flag}",
            )
            app.db.session.add(solve)
            app.db.session.commit()

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = _submit(client, chal_id, "CTF{flag}")

            assert resp.status_code == 409
            data = json.loads(resp.data)
            assert data["success"] is False
            assert "already" in data["message"].lower()
        destroy_ctfd(app)

    def test_unauthenticated_submission_redirects(self):
        app = create_ctfd()
        with app.app_context():
            chal = gen_challenge(app.db, name="Rev 101", category="Rev")
            chal_id = chal.id
            gen_flag(app.db, chal_id, content="CTF{flag}")

        with app.app_context():
            with app.test_client() as client:
                resp = _submit(client, chal_id, "CTF{flag}")

            assert resp.status_code in (302, 403)
        destroy_ctfd(app)

    def test_empty_flag_returns_400(self):
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="Forensics 101", category="Forensics")
            chal_id = chal.id
            gen_flag(app.db, chal_id, content="CTF{flag}")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = client.post(
                    f"/api/challenges/{chal_id}/submit-flag",
                    json={"flag": ""},
                    headers={"Content-Type": "application/json"},
                )

            assert resp.status_code == 400
            data = json.loads(resp.data)
            assert data["success"] is False
        destroy_ctfd(app)

    def test_nonexistent_challenge_returns_404(self):
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = _submit(client, 99999, "CTF{flag}")

            assert resp.status_code == 404
        destroy_ctfd(app)

    def test_solve_record_created_on_correct_flag(self):
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="Web XSS", category="Web")
            chal_id = chal.id
            user_id = user.id
            gen_flag(app.db, chal_id, content="CTF{xss}")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                _submit(client, chal_id, "CTF{xss}")

            solve = Solves.query.filter_by(
                challenge_id=chal_id, user_id=user_id
            ).first()
            assert solve is not None
            assert solve.provided.lower() == "ctf{xss}"
        destroy_ctfd(app)

    def test_attempt_alias_route_works(self):
        """POST /api/challenges/<id>/attempt is also a valid route."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="Crypto AES", category="Crypto")
            chal_id = chal.id
            gen_flag(app.db, chal_id, content="CTF{aes}")

        with app.app_context():
            with app.test_client() as client:
                _login(client)
                resp = _submit(client, chal_id, "CTF{aes}", route="attempt")

            assert resp.status_code == 200
            assert json.loads(resp.data)["success"] is True
        destroy_ctfd(app)

    def test_response_format_is_consistent(self):
        """All responses must have success, message keys."""
        app = create_ctfd()
        with app.app_context():
            gen_user(app.db, name="player1", email="p1@test.com")
            chal = gen_challenge(app.db, name="Misc Trivia", category="Misc")
            chal_id = chal.id
            gen_flag(app.db, chal_id, content="CTF{trivia}")

        with app.app_context():
            with app.test_client() as client:
                _login(client)

                for flag in ("CTF{trivia}", "wrong_flag"):
                    resp = _submit(client, chal_id, flag)
                    data = json.loads(resp.data)
                    assert "success" in data
                    assert "message" in data
                    assert isinstance(data["success"], bool)
        destroy_ctfd(app)
