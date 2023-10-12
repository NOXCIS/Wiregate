from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, HiddenField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    username = StringField('username', validators=[])
    password = StringField('username', validators=[DataRequired()])


class DeleteUser(FlaskForm):
    username = HiddenField('username', validators=[DataRequired()])


class PasswordForm(FlaskForm):
    username = HiddenField('username', validators=[DataRequired()])
    password = StringField('password', validators=[DataRequired()])


class MessageForm(FlaskForm):
    message = StringField('message', validators=[DataRequired()])