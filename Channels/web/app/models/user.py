"""
Module containing the class of the user model.
"""
from typing import Optional

from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer, SignatureExpired, BadSignature
from os import environ

from .base import db

# If the user has not uploaded own profile picture,
# this default one (in static/img/profile_pictures) will be used.
DEFAULT_PROFILE_PICTURE = 'default.png'

class User(db.Model, UserMixin):
    """Model of the user of the app.

    Fields:
        id (int): Primary key of the user.\n
        username (str): Name of the user.\n
        email (str): Email of the user.\n
        password (str): Password of the user.\n
        profile_picture (str): Relative path to the profile picture of the user.

    Relationships:
        messages: All messages the user sent. One to many relationship with Message model.\n
        allowed_channels: All channels the user is allowed to see.

    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    profile_picture = db.Column(db.String(20), nullable=False, default=DEFAULT_PROFILE_PICTURE)

    messages = db.relationship('Message', backref='user', lazy=True)
    allowed_channels = db.relationship('ChannelAllowList', backref='user', lazy=True)

    def __repr__(self) -> str:
        """Get representation of a user.

        Returns:
            String representation of a user.

        """
        return f"User(name='{self.username}')"

    def generate_api_token(self, expiration: int = 604800) -> str:
        """Generate the token for API valid for the given number of seconds.

        Args:
            expiration: The number of seconds saying how long the token should be valid.

        Returns:
            The user's individual API token.

        """
        s = Serializer(environ['SECRET_KEY'], expires_in=expiration, salt='api_token')
        return s.dumps({'id': self.id}).decode('utf8')

    @staticmethod
    def verify_api_token(token: str) -> Optional['User']:
        """Verify the given API token and if it is valid return the user assigned to the token.

        Args:
            token: The token to be verified.

        Returns:
            Either the matched user or None.

        """
        s = Serializer(environ['SECRET_KEY'], salt='api_token')
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None  # valid token, but expired
        except BadSignature:
            return None  # invalid token
        user = User.query.get(data['id'])
        return user
