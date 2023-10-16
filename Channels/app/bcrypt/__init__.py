"""
This package contains all modules related to Bcrypt.
This particular module initialize Bcrypt in the app.
"""

from flask import Flask
from .base import bcrypt

def init_app(app: Flask) -> None:
    """Initialize Bcrypt in the app.

    Args:
        app: Flask application where Bcrypt should be work in.

    """
    bcrypt.init_app(app)
