"""
Module containing class of the channel model.
"""

from .base import db

class Channel(db.Model):
    """Model of the channel for storing messages.

    Fields:
        id (int): Primary key of the channel.\n
        name (str): Name of the channel. Cannot be longer than 30 characters.\n
        password (str): Hashed password of the channel.

    Relationships:
        messages: All messages the channel has.
        One to many relationship with Message model.\n

        allowed_users: All users who are allowed to see the channel.
        One to many relationship with ChannelAllowList model.

    """
    __tablename__ = 'channels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(60), unique=True, nullable=False)

    messages = db.relationship('Message', backref='channel', cascade='all,delete-orphan', lazy=True)
    allowed_users = db.relationship('ChannelAllowList', backref='channel', lazy=True)

    def __repr__(self) -> str:
        """Get representation of a channel.

        Returns:
            String representation of a channel.

        """
        return f"Channel(name='{self.name}')"
