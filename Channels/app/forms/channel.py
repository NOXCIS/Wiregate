"""
Module containing the classes of the forms to add and update a channel.
"""

import re

from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, ValidationError, Length, EqualTo

from app.models import Channel, ChannelAllowList

class ChannelForm(FlaskForm):
    """Base channel form class with methods to validate the email."""

    @staticmethod
    def _channel_has_invalid_name(name: str) -> bool:
        """Check if the channel has invalid name. Its name is invalid if either it is empty,
        has trailing or leading spaces, or violates the `valid_pattern` regex.

        Args:
            name: Name of the channel to be checked.

        Returns:
            True if it has invalid name, False otherwise.

        """
        valid_pattern = re.compile(r'[A-Za-z0-9 \-_]+')

        if not name:
            return True
        else:
            return not(bool(re.fullmatch(valid_pattern, name))) \
                   or name.startswith(' ') \
                   or name.endswith(' ')

    @staticmethod
    def _channel_already_exists(name: str) -> bool:
        """Check if the channel already exists in the database.

        Args:
            name: Name of the channel to be checked.

        Returns:
            True if it already exists, false otherwise.

        """
        channel = Channel.query.filter_by(name=name).first()
        return bool(channel)


class AddChannelForm(ChannelForm):
    """Form to create a new channel.

    Fields:
        name: The name of the channel.\n
        password: The password of the channel.\n
        confirm_password: The same password repeated for the second time.\n
        submit_add: The submit button to send the form.
    """
    name = StringField('Name of the new channel', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')
    ])
    submit_add = SubmitField('Add now!')

    def validate_name(self, name: StringField) -> None:
        """Check if the filled name of the channel is valid.

        The name of the channel is valid if it is unique and of the appropriate form.

        Args:
            name: The filled form of a channel.

        Raises:
            ValidationError: If the name is not valid.

        """
        if self._channel_already_exists(name.data):
            raise ValidationError('This channel name is taken. Choose a different one.')
        elif self._channel_has_invalid_name(name.data):
            raise ValidationError('Name of the channel is invalid.')

class JoinChannelForm(ChannelForm):
    """Form to join a channel.

    Fields:
        name: The name of the channel.\n
        password: The password of the channel.\n
        submit_join: The submit button to join the channel.
    """
    name = StringField('Name of the new channel', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit_join = SubmitField('Join now!')

    def validate_name(self, name: StringField) -> None:
        """Check if the filled name is not among the channels the user already has access to.

        Args:
            name: The filled name of the channel.

        Raises:
            ValidationError: If the name is not valid.

        """
        if channel := Channel.query.filter_by(name=name.data).first():
            if ChannelAllowList.query.filter_by(user_id=current_user.id).filter_by(channel_id=channel.id).first():
                raise ValueError("You are already member of this channel.")

class UpdateChannelForm(ChannelForm):
    """Form to update an existing channel.

    Fields:
        name: The name of the channel.\n
        submit_update: The submit button to update the channel.
    """
    name = StringField('New name of the channel', validators=[DataRequired()])
    submit_update = SubmitField('Update the channel')

    def validate_name(self, name: StringField) -> None:
        """Check if the filled name of the channel is valid.

        The name of the channel is valid if it is unique and of the appropriate form.

        Args:
            name: The filled form of a channel.

        Raises:
            ValidationError: If the name is not valid.

        """
        if self._channel_already_exists(name.data):
            raise ValidationError('This channel name is either taken or the current name. Choose a different one.')
        elif self._channel_has_invalid_name(name.data):
            raise ValidationError('Name of the channel is invalid.')
