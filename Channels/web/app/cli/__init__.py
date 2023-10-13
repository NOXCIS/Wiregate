"""
Module containing the extension to the command line interface of the app.
This particular module register the blueprint.
"""

from .bp import cli_bp
from flask import Flask

def init_app(app: Flask) -> None:
    """Initialize cli blueprint in the app.

    Args:
        app: Flask application where cli blueprint should be initialized in.

    """
    app.register_blueprint(cli_bp)
