"""
Module containing the model storing permits for users to see channels.
Along with that, it has a helper enum saying what role the user has.
"""

from enum import Enum

from .base import db

class UserRole(Enum):
    """Describe the user role in the channel.
    The user can either be a normal user without privileges or can be an admin.
    """
    NORMAL_USER = 1
    ADMIN = 2

class ChannelAllowList(db.Model):
    """Allow list model saying which users can see a certain channel.

    Fields:
        id (int): Primary key of the allow list.\n
        user_role (UserRole enum): Role the user has in the channel.\n
        channel_id (foreign key): Id of the channel the user is allowed to see.\n
        user_id (foreign key): Id of the user who can see the channel.

    """
    __tablename__ = 'channel_allowlist'
    id = db.Column(db.Integer, primary_key=True)
    user_role = db.Column(db.Integer, db.Enum(UserRole), nullable=False, default=UserRole.NORMAL_USER.value)

    channel_id = db.Column(db.Integer, db.ForeignKey('channels.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    member = db.relationship('User', lazy=True)

    def __repr__(self) -> str:
        """Get representation of a record of the allow list.

        Returns:
            String representation of a record of the allow list.

        """

        return ("ChannelAllowList(" +
                f"channel_id={self.channel_id}, user_id={self.user_id}, user_role={self.user_role}" +
                ")")
