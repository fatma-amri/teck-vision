"""
Pytest fixtures shared across all Teck-Vision tests.
"""
import datetime

import pytest

from tests.helpers import create_ctfd, destroy_ctfd, gen_challenge, gen_user


@pytest.fixture(scope="function")
def app():
    """Create a fresh Flask application for each test."""
    application = create_ctfd()
    yield application
    destroy_ctfd(application)


@pytest.fixture(scope="function")
def client(app):
    """A test client for the Flask application."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Application database session."""
    with app.app_context():
        yield app.db


@pytest.fixture(scope="function")
def auth_user(app):
    """A regular logged-in test user (returns (client, user) tuple)."""
    with app.app_context():
        user = gen_user(app.db, name="player1", email="player1@ctf.test")
    client = app.test_client()
    with app.app_context():
        client.get("/login", follow_redirects=True)
        client.post(
            "/login",
            data={"name": "player1", "password": "password"},
            follow_redirects=True,
        )
    return client, user


@pytest.fixture(scope="function")
def admin_user(app):
    """An admin test user (returns (client, user) tuple)."""
    with app.app_context():
        from CTFd.models import Users
        user = gen_user(app.db, name="admin1", email="admin1@ctf.test")
        with app.app_context():
            Users.query.filter_by(id=user.id).update({"type": "admin"})
            app.db.session.commit()
    client = app.test_client()
    client.get("/login", follow_redirects=True)
    client.post(
        "/login",
        data={"name": "admin1", "password": "password"},
        follow_redirects=True,
    )
    return client, user


@pytest.fixture(scope="function")
def sample_challenge(app):
    """A visible standard challenge with a static flag."""
    with app.app_context():
        chal = gen_challenge(
            app.db,
            name="Test Challenge",
            description="A test challenge",
            value=100,
            category="Web",
            state="visible",
        )
        from CTFd.models import Flags
        flag = Flags(challenge_id=chal.id, type="static", content="CTF{test_flag}")
        app.db.session.add(flag)
        app.db.session.commit()
        return chal


@pytest.fixture(scope="function")
def sample_room(app):
    """A sample Room record in the database."""
    with app.app_context():
        from CTFd.models import Rooms
        room = Rooms(
            name="Web Security Challenge",
            slug="web-security-challenge",
            description="Practice web security fundamentals.",
            difficulty="Easy",
            duration=30,
            target_ip="15.237.60.47",
        )
        app.db.session.add(room)
        app.db.session.commit()
        return room


@pytest.fixture(scope="function")
def running_instance(app, sample_room):
    """An active RoomInstance tied to sample_room."""
    with app.app_context():
        from CTFd.models import RoomInstances
        user = gen_user(app.db, name="runner", email="runner@ctf.test")
        instance = RoomInstances(
            user_id=user.id,
            category=sample_room.slug,
            machine_ip="15.237.60.47",
            is_active=True,
            started_at=datetime.datetime.utcnow(),
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
            duration_minutes=30,
        )
        app.db.session.add(instance)
        app.db.session.commit()
        return instance, user


@pytest.fixture(scope="function")
def expired_instance(app, sample_room):
    """An expired RoomInstance (expires_at in the past)."""
    with app.app_context():
        from CTFd.models import RoomInstances
        user = gen_user(app.db, name="expired_user", email="expired@ctf.test")
        instance = RoomInstances(
            user_id=user.id,
            category=sample_room.slug,
            machine_ip="15.237.60.47",
            is_active=True,
            started_at=datetime.datetime.utcnow() - datetime.timedelta(hours=2),
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
            duration_minutes=30,
        )
        app.db.session.add(instance)
        app.db.session.commit()
        return instance, user
