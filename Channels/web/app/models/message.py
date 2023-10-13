"""
Module containing class of the message model.
"""

from .base import db

class Message(db.Model):
    """Model of the message users sent to channels.

    Fields:
        id (int): Primary key of the message.\n
        content (str): Content of the message.\n
        time (DateTime): Time when the message was sent.\n
        user_id (foreign key): ID of the user who sent the message.\n
        channel_id (foreign key): Id of the channel the message was sent to.

    """
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author = db.relationship('User', lazy=True)
    target_channel = db.Column(db.Integer, db.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self) -> str:
        """Get representation of a message.

        Returns:
            String representation of a message.

        """
        return f"Message(author_id={self.author_id}, target_channel={self.target_channel}, time={self.time})"
