"""
Health check endpoints for Kubernetes probes and monitoring
"""
from flask import Blueprint, jsonify
from CTFd.models import db

health = Blueprint("health", __name__)


@health.route("/health", methods=["GET"])
def healthcheck():
    """
    Liveness probe endpoint for Kubernetes
    Returns 200 if the application is running
    """
    return jsonify({"status": "healthy", "service": "teck-vision"}), 200


@health.route("/ready", methods=["GET"])
def readiness():
    """
    Readiness probe endpoint for Kubernetes
    Checks database connectivity before returning success
    """
    try:
        # Test database connection
        db.session.execute(db.select([1]))
        return jsonify({"status": "ready", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "not ready", "error": str(e)}), 503
