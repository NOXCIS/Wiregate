"""
Module containing the login form class.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email

class LoginForm(FlaskForm):
    """Form shown when user want to sign in.

    Fields:
        email: Email of the user.\n
        password: Password of the user.\n
        remember: Checkbox saying if the app should remember that the user is logged in.
        submit: Submit the form.\n

    """
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Log in')
