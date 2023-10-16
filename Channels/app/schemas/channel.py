"""
Module containing the schema of the channel model.
"""

from .base import ma
from app.models import Channel
from .channel_allowlist import ChannelAllowListSchema
from .message import MessageSchema

class ChannelSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Channel
        ordered = True

    name = ma.auto_field()
    allowed_users = ma.Nested(ChannelAllowListSchema, many=True)
    messages = ma.Nested(MessageSchema, many=True)
