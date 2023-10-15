"""
Module containing the form to update the user's profile.
"""

from flask_wtf import FlaskForm
from sqlalchemy import func
from wtforms import StringField, SubmitField, ValidationError
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired, Length, Email
from flask_login import current_user

from app.models.user import User

class UpdateProfileForm(FlaskForm):
    """Form to update the data of a user.

    Fields:
        username: Name of the user.\n
        email: Email of the user.\n
        profile_picture: File which will be profile picture of a user.\n
        submit: Submit the form.\n

    """
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    profile_picture = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'png'], 'You can only add images!')])
    submit = SubmitField('Update')

    def validate_username(self, username: StringField) -> None:
        """Check if the given username is valid.

        The username is valid if it is unique.

        Args:
            username: The username provided in the registration form.

        Raises:
            ValidationError: If the username is invalid.

        """
        user = User.query.filter(func.lower(User.username) == func.lower(username.data)).first()
        if user != current_user:
            if user:
                raise ValidationError('This username is taken. Choose a different one.')

    def validate_email(self, email: StringField) -> None:
        """Check if the given email is valid.

        The email is valid if it is unique.

        Args:
            email: The email provided in the registration form.

        Raises:
            ValidationError: If the email is invalid.

        """
        user = User.query.filter(func.lower(User.email) == func.lower(email.data)).first()
        if user != current_user:
            if user:
                raise ValidationError('This email is taken. Choose a different one.')
