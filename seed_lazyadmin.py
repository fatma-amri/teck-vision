"""Seed script: create LazyAdmin room with 5 challenges using RoomChallenge model."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def seed():
    from CTFd.models import RoomChallenge, Rooms, db

    room_data = {
        "name": "LazyAdmin",
        "slug": "lazyadmin",
        "description": (
            "A beginner-friendly Linux machine. Exploit a misconfigured service, "
            "gain a foothold, escalate to root, and capture both flags."
        ),
        "difficulty": "Easy",
        "duration": 45,
        "target_ip": "15.237.60.47",
        "is_active": True,
    }

    challenges_data = [
        {
            "title": "Initial Access",
            "description": "Gain your initial foothold on the target machine.",
            "question": "What user provided the reverse shell?",
            "answer": "ben",
            "points": 100,
            "difficulty": "Easy",
            "position": 1,
        },
        {
            "title": "User Flag",
            "description": "Find the user flag on the target machine.",
            "question": "What is the user flag?",
            "answer": "Koussay",
            "points": 100,
            "difficulty": "Easy",
            "position": 2,
        },
        {
            "title": "Vulnerability Discovery",
            "description": "Identify the vulnerability that allowed initial access.",
            "question": "What vulnerability allowed initial access?",
            "answer": "unauthenticated Redis service",
            "points": 150,
            "difficulty": "Medium",
            "position": 3,
        },
        {
            "title": "Privilege Escalation",
            "description": "Escalate your privileges to root.",
            "question": "How was privilege escalation achieved?",
            "answer": "SSH private key",
            "points": 150,
            "difficulty": "Medium",
            "position": 4,
        },
        {
            "title": "Root Flag",
            "description": "Capture the root flag to complete the room.",
            "question": "What is the root flag?",
            "answer": "cf537b04dd79e859816334b89e85c435",
            "points": 100,
            "difficulty": "Easy",
            "position": 5,
        },
    ]

    # Create or update room
    room = Rooms.query.filter_by(slug=room_data["slug"]).first()
    if not room:
        room = Rooms(**room_data)
        db.session.add(room)
        db.session.flush()
        print(f"[+] Created room: {room_data['name']}")
    else:
        for k, v in room_data.items():
            setattr(room, k, v)
        db.session.flush()
        print(f"[~] Updated room: {room_data['name']}")

    for chal_data in challenges_data:
        existing = RoomChallenge.query.filter_by(
            room_id=room.id, title=chal_data["title"]
        ).first()

        if existing:
            for k, v in chal_data.items():
                setattr(existing, k, v)
            print(f"[~] Updated challenge: {chal_data['title']}")
        else:
            challenge = RoomChallenge(room_id=room.id, **chal_data)
            db.session.add(challenge)
            print(f"[+] Created challenge: {chal_data['title']}")

    db.session.commit()
    print("[✓] LazyAdmin seed complete.")


if __name__ == "__main__":
    from CTFd import create_app

    app = create_app()
    with app.app_context():
        seed()
