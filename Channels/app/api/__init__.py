"""
This package has all routes and utility functions of the "API" blueprint.
Everything in this package is connected to API key, and GET answers for requests of users.

This particular module contains the registration of the "API" blueprint.
"""

from .routes import api
from flask import Flask

def init_app(app: Flask) -> None:
    """Initialize API routes with their functionality in the application.

    Args:
        app: Flask application where routes should be initialized in.

    """
    app.register_blueprint(api)
