"""Seed script: create LazyAdmin room with 5 challenges."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def seed():
    from CTFd.models import Challenges, Flags, Rooms, db

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
    }

    challenges_data = [
        {
            "name": "Initial Access",
            "description": "What user provided the reverse shell?",
            "answer": "ben",
            "points": 100,
            "position": 1,
        },
        {
            "name": "User Flag",
            "description": "What is the user flag?",
            "answer": "Koussay",
            "points": 100,
            "position": 2,
        },
        {
            "name": "Vulnerability Discovery",
            "description": "What vulnerability allowed the initial access?",
            "answer": "unauthenticated Redis service",
            "points": 150,
            "position": 3,
        },
        {
            "name": "Privilege Escalation",
            "description": "How was privilege escalation to root achieved?",
            "answer": "SSH private key",
            "points": 150,
            "position": 4,
        },
        {
            "name": "Root Flag",
            "description": "What is the root flag?",
            "answer": "cf537b04dd79e859816334b89e85c435",
            "points": 100,
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
        print(f"[~] Updated room: {room_data['name']}")

    for chal_data in challenges_data:
        existing = Challenges.query.filter_by(
            name=chal_data["name"], category=room_data["slug"]
        ).first()

        if existing:
            print(f"[~] Challenge already exists: {chal_data['name']}")
            challenge = existing
        else:
            challenge = Challenges(
                name=chal_data["name"],
                description=chal_data["description"],
                category=room_data["slug"],
                value=chal_data["points"],
                position=chal_data["position"],
                type="standard",
                state="visible",
            )
            db.session.add(challenge)
            db.session.flush()
            print(f"[+] Created challenge: {chal_data['name']}")

        # Ensure flag exists
        existing_flag = Flags.query.filter_by(challenge_id=challenge.id).first()
        if not existing_flag:
            flag = Flags(
                challenge_id=challenge.id,
                type="static",
                content=chal_data["answer"],
            )
            db.session.add(flag)
        else:
            existing_flag.content = chal_data["answer"]

    db.session.commit()
    print("[✓] LazyAdmin seed complete.")


if __name__ == "__main__":
    from CTFd import create_app

    app = create_app()
    with app.app_context():
        seed()
