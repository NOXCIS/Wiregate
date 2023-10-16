"""
This package contains all routes and utility functions used by
the "main" blueprint. This blueprint is responsible for the main behaviour
of the application (no login/registering, settings of the user account).

This particular module registers the "main" blueprint.
"""

from .routes import main
from flask import Flask

def init_app(app: Flask) -> None:
    """Initialize "main" blueprint with their functionality in the application.

    Args:
        app: Flask application where the blueprint should be initialized in.

    """
    app.register_blueprint(main)
