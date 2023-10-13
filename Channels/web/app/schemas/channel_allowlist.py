"""
Module containing the schema of the channel model.
"""

from .base import ma
from app.models import ChannelAllowList
from .user import UserSchema

class ChannelAllowListSchema(ma.SQLAlchemySchema):
    class Meta:
        model = ChannelAllowList

    user_role = ma.auto_field()
    member = ma.Nested(UserSchema)
