"""
All routes of the "login" blueprint.
"""

from flask import render_template, flash, url_for, redirect, request
from flask_login import login_user, current_user, logout_user, login_required

from typing import Union
from werkzeug.wrappers import Response

from .base import login
from .utils import add_user, is_valid_user, get_number_of_all_messages, get_number_of_all_channels,\
    update_user, save_profile_picture, remove_old_profile_picture

from app.forms.registration import RegistrationForm
from app.forms.login import LoginForm
from app.forms.update_profile import UpdateProfileForm

from app.models.user import User

@login.route('/', methods=['GET', 'POST'])
def index() -> Union[Response, str]:
    """Handle the login process.

    Opened with GET:
        Check if the user is logged in. If it is, redirect to the app.
        Otherwise, render template to log in.

    Opened with POST:
        Get 'username' parameter from the POST form. Log in user of a given 'username'
        and redirect her/him to app if she/he entered valid credentials. Otherwise, show
        message that login was unsuccessful.

    Returns:
        By default, the rendered login page.
        If received valid POST form, the rendered app page.

    """
    if current_user.is_authenticated:
        return redirect(url_for('main.setup_app'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if is_valid_user(user, form):
            login_user(user=user, remember=form.remember)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.setup_app'))
        else:
            flash('Login Unsuccessful. Incorrect email or password.', 'danger')

    return render_template('login.html', form=form)

@login.route('/register', methods=['GET', 'POST'])
def register() -> Union[Response, str]:
    """Handle the registration process.

    Opened with GET:
        Render the registration form.

    Opened with POST:
        Create the user and redirect to the login page. Otherwise, show what was invalid in the form.

    Returns:
        By default, the rendered registration page.
        If received valid POST form, the redirection to the login page.

    """
    form = RegistrationForm()
    if form.validate_on_submit():
        add_user(form)
        flash(f'An account was successfully created for {form.username.data}!', 'success')
        return redirect(url_for('login.index'))
    else:
        return render_template('register.html', form=form)

@login.route('/log-out')
@login_required
def log_out() -> Response:
    """Log out the current user and redirect to the login page.

    Returns:
        Redirection to the login page.

    """
    logout_user()
    return redirect(url_for('login.index'))

@login.route('/settings', methods=['GET', 'POST'])
@login_required
def settings() -> Union[str, Response]:
    """Render the settings page when the user is logged in.

    Returns:
        The rendered settings page.

    """
    all_messages = get_number_of_all_messages()
    all_channels = get_number_of_all_channels()

    form = UpdateProfileForm()
    if form.validate_on_submit():
        if form.profile_picture.data:
            remove_old_profile_picture()
            profile_picture = save_profile_picture(form.profile_picture.data)
            current_user.profile_picture = profile_picture
        update_user(form.username.data, form.email.data)
        flash('Your profile has been successfully updated.', 'success')
        return redirect(url_for('login.settings'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    return render_template('settings-user.html', all_messages=all_messages, all_channels=all_channels, form=form)
