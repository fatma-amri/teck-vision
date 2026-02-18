#!/usr/bin/env python
"""
Teck-Vision — Commandes CLI Flask
Plateforme CTF DevSecOps

Usage:
    python manage.py shell
    python manage.py db upgrade
"""
from flask.cli import FlaskGroup

from CTFd import create_app

app = create_app()

cli = FlaskGroup(app)


if __name__ == "__main__":
    cli()
