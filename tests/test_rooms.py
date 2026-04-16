"""
Tests manuels et automatisés pour le système de Rooms.

Exécuter avec: pytest tests/test_rooms.py -v
"""

import json
from datetime import datetime, timedelta

import pytest

from CTF.models import Challenges, Flags, RoomInstances, Solves, db
from tests.helpers import create_ctfd, destroy_ctfd, gen_user, gen_challenge


class TestRoomInstances:
    """Tests pour le contrôle des machines."""

    def test_start_machine(self):
        """Tester le démarrage d'une machine."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="player1@example.com")
            
            with app.test_client() as client:
                client.get("/login", follow_redirects=True)
                client.post(
                    "/login",
                    data={"name": "player1", "password": "password"},
                    follow_redirects=True,
                )
                
                # Start machine
                response = client.post(
                    "/api/room-instances/start/web-security-challenge",
                    json={},
                    headers={"Content-Type": "application/json"},
                )
                
                assert response.status_code == 201
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["machine_ip"] == "15.237.60.47"
                assert data["time_remaining"] > 0
        
        destroy_ctfd(app)

    def test_stop_machine(self):
        """Tester l'arrêt d'une machine."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="player1@example.com")
            
            # Create active instance
            instance = RoomInstances(
                user_id=user.id,
                category="web-security-challenge",
                machine_ip="15.237.60.47",
                is_active=True,
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=30),
            )
            app.db.session.add(instance)
            app.db.session.commit()
            
            with app.test_client() as client:
                client.get("/login", follow_redirects=True)
                client.post(
                    "/login",
                    data={"name": "player1", "password": "password"},
                    follow_redirects=True,
                )
                
                # Stop machine
                response = client.post(
                    "/api/room-instances/terminate/web-security-challenge",
                    json={},
                    headers={"Content-Type": "application/json"},
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
        
        destroy_ctfd(app)

    def test_check_machine_status(self):
        """Tester la vérification du statut d'une machine."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="player1@example.com")
            
            with app.test_client() as client:
                client.get("/login", follow_redirects=True)
                client.post(
                    "/login",
                    data={"name": "player1", "password": "password"},
                    follow_redirects=True,
                )
                
                # Check status (should be inactive)
                response = client.get(
                    "/api/room-instances/status/web-security-challenge",
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["is_active"] is False
        
        destroy_ctfd(app)


class TestFlagSubmission:
    """Tests pour la soumission de flags."""

    def test_submit_correct_flag(self):
        """Tester la soumission d'un flag correct."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="player1@example.com")
            challenge = gen_challenge(app.db, name="Challenge 1", category="web-security")
            
            # Create flag
            flag = Flags(
                challenge_id=challenge.id,
                type="static",
                content="correct_flag",
            )
            app.db.session.add(flag)
            app.db.session.commit()
            
            with app.test_client() as client:
                client.get("/login", follow_redirects=True)
                client.post(
                    "/login",
                    data={"name": "player1", "password": "password"},
                    follow_redirects=True,
                )
                
                # Submit flag
                response = client.post(
                    f"/api/challenges/{challenge.id}/submit-flag",
                    json={"flag": "correct_flag"},
                    headers={"Content-Type": "application/json"},
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert "points" in data
                
                # Verify solve was created
                solve = Solves.query.filter_by(
                    challenge_id=challenge.id,
                    user_id=user.id,
                ).first()
                assert solve is not None
        
        destroy_ctfd(app)

    def test_submit_incorrect_flag(self):
        """Tester la soumission d'un flag incorrect."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="player1@example.com")
            challenge = gen_challenge(app.db, name="Challenge 1", category="web-security")
            
            # Create flag
            flag = Flags(
                challenge_id=challenge.id,
                type="static",
                content="correct_flag",
            )
            app.db.session.add(flag)
            app.db.session.commit()
            
            with app.test_client() as client:
                client.get("/login", follow_redirects=True)
                client.post(
                    "/login",
                    data={"name": "player1", "password": "password"},
                    follow_redirects=True,
                )
                
                # Submit wrong flag
                response = client.post(
                    f"/api/challenges/{challenge.id}/submit-flag",
                    json={"flag": "wrong_flag"},
                    headers={"Content-Type": "application/json"},
                )
                
                assert response.status_code == 400
                data = json.loads(response.data)
                assert data["success"] is False
                assert "Wrong flag" in data["message"]
        
        destroy_ctfd(app)

    def test_flag_case_insensitive(self):
        """Tester que la validation des flags est insensible à la casse."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="player1@example.com")
            challenge = gen_challenge(app.db, name="Challenge 1", category="web-security")
            
            # Create flag
            flag = Flags(
                challenge_id=challenge.id,
                type="static",
                content="FLAG_VALUE",
            )
            app.db.session.add(flag)
            app.db.session.commit()
            
            with app.test_client() as client:
                client.get("/login", follow_redirects=True)
                client.post(
                    "/login",
                    data={"name": "player1", "password": "password"},
                    follow_redirects=True,
                )
                
                # Submit lowercase
                response = client.post(
                    f"/api/challenges/{challenge.id}/submit-flag",
                    json={"flag": "flag_value"},
                    headers={"Content-Type": "application/json"},
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
        
        destroy_ctfd(app)

    def test_already_solved_challenge(self):
        """Tester qu'on ne peut pas soumettre deux fois un challenge."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="player1@example.com")
            challenge = gen_challenge(app.db, name="Challenge 1", category="web-security")
            
            # Create flag
            flag = Flags(
                challenge_id=challenge.id,
                type="static",
                content="correct_flag",
            )
            app.db.session.add(flag)
            
            # Create existing solve
            solve = Solves(
                user_id=user.id,
                challenge_id=challenge.id,
                ip="127.0.0.1",
                provided="correct_flag",
            )
            app.db.session.add(solve)
            app.db.session.commit()
            
            with app.test_client() as client:
                client.get("/login", follow_redirects=True)
                client.post(
                    "/login",
                    data={"name": "player1", "password": "password"},
                    follow_redirects=True,
                )
                
                # Try to submit again
                response = client.post(
                    f"/api/challenges/{challenge.id}/submit-flag",
                    json={"flag": "correct_flag"},
                    headers={"Content-Type": "application/json"},
                )
                
                assert response.status_code == 409
                data = json.loads(response.data)
                assert data["success"] is False
                assert "already solved" in data["message"].lower()
        
        destroy_ctfd(app)


class TestRoomPage:
    """Tests pour la page de détail de la room."""

    def test_room_detail_page_loads(self):
        """Tester que la page de détail d'une room se charge."""
        app = create_ctfd()
        with app.app_context():
            user = gen_user(app.db, name="player1", email="player1@example.com")
            challenge = gen_challenge(
                app.db,
                name="Challenge 1",
                category="web-security",
                value=100,
            )
            
            with app.test_client() as client:
                client.get("/login", follow_redirects=True)
                client.post(
                    "/login",
                    data={"name": "player1", "password": "password"},
                    follow_redirects=True,
                )
                
                # Access room page
                response = client.get("/rooms/web-security", follow_redirects=True)
                
                assert response.status_code == 200
                assert b"Challenge 1" in response.data
                assert b"Demarrer le challenge" in response.data
        
        destroy_ctfd(app)


# ============================================================================
# TEST COMMANDS
# ============================================================================

"""
Run individual tests:

pytest tests/test_rooms.py::TestRoomInstances::test_start_machine -v
pytest tests/test_rooms.py::TestFlagSubmission::test_submit_correct_flag -v
pytest tests/test_rooms.py::TestRoomPage::test_room_detail_page_loads -v

Run all room tests:
pytest tests/test_rooms.py -v

Run with coverage:
pytest tests/test_rooms.py --cov=CTF/room_instances --cov=CTF/challenges_api
"""
