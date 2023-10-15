"""
Module containing the schema of the message model.
"""

from .base import ma
from .user import UserSchema
from app.models import Message

class MessageSchema(ma.SQLAlchemySchema):
    class Meta:
        model = Message
        ordered = True

    author = ma.Nested(UserSchema)
    time = ma.auto_field()
    content = ma.auto_field()
