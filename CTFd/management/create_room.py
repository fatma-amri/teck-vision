"""Management commands for setting up room challenges with flags."""

import logging

from CTFd.models import Challenges, Flags, db

logger = logging.getLogger(__name__)


def create_room_with_challenges():
    """Create a sample room with 5 challenges and their flags.
    
    This can be called from CLI or admin endpoint to populate test data.
    """
    
    # Room metadata
    room_category = "Web Security Challenge"
    room_description = "Complete web security challenges to exploit the vulnerable machine."
    
    challenges_data = [
        {
            "name": "Initial Access",
            "description": "What user provided the reverse shell?",
            "flag": "ben",
            "points": 100,
            "position": 1,
        },
        {
            "name": "User Flag",
            "description": "What is the user flag?",
            "flag": "Koussay",
            "points": 100,
            "position": 2,
        },
        {
            "name": "Vulnerability Discovery",
            "description": "What vulnerability allowed the initial access to the machine?",
            "flag": "unauthenticated Redis service",
            "points": 150,
            "position": 3,
        },
        {
            "name": "Privilege Escalation",
            "description": "How was privilege escalation to root achieved?",
            "flag": "SSH private key",
            "points": 150,
            "position": 4,
        },
        {
            "name": "Root Flag",
            "description": "What is the root flag?",
            "flag": "cf537b04dd79e859816334b89e85c435",
            "points": 100,
            "position": 5,
        },
    ]
    
    try:
        # Create challenges
        for chal_data in challenges_data:
            # Check if challenge already exists
            existing = Challenges.query.filter_by(
                name=chal_data["name"],
                category=room_category
            ).first()
            
            if existing:
                logger.info(f"Challenge '{chal_data['name']}' already exists. Skipping.")
                continue
            
            challenge = Challenges(
                name=chal_data["name"],
                description=chal_data["description"],
                category=room_category,
                value=chal_data["points"],
                position=chal_data["position"],
                type="standard",
                state="visible",
            )
            
            db.session.add(challenge)
            db.session.flush()  # Get the ID
            
            # Create flag for the challenge
            flag = Flags(
                challenge_id=challenge.id,
                type="static",
                content=chal_data["flag"],
            )
            
            db.session.add(flag)
            logger.info(f"Created challenge: {chal_data['name']}")
        
        db.session.commit()
        logger.info("Room challenges created successfully!")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating room challenges: {str(e)}")
        return False


if __name__ == "__main__":
    # For manual CLI usage
    from CTFd import create_app
    
    app = create_app()
    with app.app_context():
        create_room_with_challenges()
