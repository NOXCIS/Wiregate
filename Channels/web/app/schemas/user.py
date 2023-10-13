"""
Module containing the schema of the message model.
"""

from .base import ma
from app.models import User

class UserSchema(ma.SQLAlchemySchema):
    class Meta:
        model = User

    username = ma.auto_field()
