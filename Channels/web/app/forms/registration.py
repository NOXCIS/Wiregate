"""
Module containing the registration form class.
"""

from sqlalchemy import func
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Length, EqualTo, DataRequired, Email, ValidationError

from app.models.user import User

class RegistrationForm(FlaskForm):
    """Form shown when user want to register.

    Fields:
        username: Name of the user.\n
        email: Email of the user.\n
        password: Password of the user.\n
        confirm_password: The same password repeated for the second time.\n
        submit: Submit the form.\n

    """
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=5)])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')

    def validate_username(self, username: StringField) -> None:
        """Check if the given username is valid.

        The username is valid if it is unique.

        Args:
            username: The username provided in the registration form.

        Raises:
            ValidationError: If the username is invalid.

        """
        user = User.query.filter(func.lower(User.username) == func.lower(username.data)).first()
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
        if user:
            raise ValidationError('This email is taken. Choose a different one.')
