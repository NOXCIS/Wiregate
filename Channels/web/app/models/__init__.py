"""
This packages has all DB models used in the app.
Module containing function which initialize database.
"""

from flask import Flask

from .base import db

from .user import User
from .message import Message
from .channel import Channel
from .channel_allowlist import ChannelAllowList

def init_app(app: Flask) -> None:
    """Initialize database in the application.

    Args:
        app: Flask application the database should be initialized in.

    """
    db.init_app(app)
