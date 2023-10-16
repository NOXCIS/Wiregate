"""
This packages has all Marshmallow schemas used in the app.
This particular module contains the function which initialize them.
"""

from flask import Flask

from .base import ma

from .channel import ChannelSchema
from .channel_allowlist import ChannelAllowListSchema
from .message import MessageSchema
from .user import UserSchema

def init_app(app: Flask) -> None:
    """Initialize schemas in the application.

    Args:
        app: Flask application the schemas should be initialized in.

    """
    ma.init_app(app)
