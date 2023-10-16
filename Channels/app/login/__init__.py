"""
This package has all routes and utility functions of the "login" blueprint.
Everything in this package is connected to login/registration and user profile management.

This particular module contains the registration of the "login" blueprint.
"""

from .routes import login
from flask import Flask

def init_app(app: Flask) -> None:
    """Initialize login routes with their functionality in the application.

    Args:
        app: Flask application where routes should be initialized in.

    """
    app.register_blueprint(login)
