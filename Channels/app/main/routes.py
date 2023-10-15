"""
All routes of the "main" blueprint.
"""

from typing import Any

from flask import request, render_template, jsonify, flash, redirect, url_for, Markup, abort, Response
from flask_login import current_user, login_required

from .base import main
from .utils import get_messages, process_add_channel_form, \
    process_join_channel_form, get_number_of_channels_users, get_number_of_channels_messages, get_channels_users, \
    is_admin, admin_manager, check_channel_settings_form, no_channel

from app.models import db, Channel, ChannelAllowList, User
from app.models.channel_allowlist import UserRole

from app.forms.channel import AddChannelForm, UpdateChannelForm, JoinChannelForm

@main.route('/app', methods=['GET', 'POST'])
@login_required
def setup_app() -> str:
    """Get username, channels and messages from database and render the main app
    template with them.

    Returns:
        The rendered template of the main app.

    """
    add_channel_form = AddChannelForm(prefix='add')
    join_channel_form = JoinChannelForm(prefix='join')
    # update_channel_form = UpdateChannelForm()

    add_channel_form_invalid = False
    join_channel_form_invalid = False
    # update_channel_form_invalid = False

    if add_channel_form.submit_add.data:
        if add_channel_form.validate_on_submit():
            process_add_channel_form(add_channel_form)
        else:
            add_channel_form_invalid = True

    elif join_channel_form.submit_join.data:
        if join_channel_form.validate_on_submit():
            process_join_channel_form(join_channel_form)
        else:
            join_channel_form_invalid = True

    # elif update_channel_form.submit_update.data:
    #     if update_channel_form.validate_on_submit():
    #         process_update_channel_form(update_channel_form)
    #     else:
    #         update_channel_form_invalid = True

    allowed_channels = ChannelAllowList.query.filter_by(user_id=current_user.id).all()
    channels = [allowed_channel.channel for allowed_channel in allowed_channels]

    return render_template(
        'app.html', username=current_user, channels=channels,

        add_channel_form=add_channel_form,
        join_channel_form=join_channel_form,
        # update_channel_form=update_channel_form,

        add_channel_form_invalid=add_channel_form_invalid,
        join_channel_form_invalid=join_channel_form_invalid,
        # update_channel_form_invalid=update_channel_form_invalid
    )

@main.route('/get-messages', methods=['POST'])
@login_required
def get_messages_ajax() -> Any:
    """Take POST form with the parameter 'channelName' and return its messages in JSON format.

    Returns:
        JSON response consisting of all messages in this channel.

    """
    channel_name = request.form.get('channelName')
    counter = request.form.get('counter')

    try:
        counter = int(counter)
    except ValueError:
        return abort(Response('Fatal error. Messages cannot be received!'))

    if counter > len(Channel.query.filter_by(name=channel_name).first().messages):
        return abort(Response('Fatal error. Messages cannot be received! Counter has exceeded the max value.'))
    else:
        return get_messages(channel_name, counter)

@main.route('/initial-counter', methods=['POST'])
@login_required
def get_initial_counter_ajax() -> Any:
    """Get the initial counter of the channel given in the form.
    The initial counter is the id of the last message to be loaded dynamically.

    Returns:
        The initial counter of the channel.

    """
    channel_name = request.form.get('channelName')
    channel = Channel.query.filter_by(name=channel_name).first()

    return jsonify({
        'counter': len(channel.messages)
    })

@main.route('/leave-channel', methods=['POST'])
@login_required
def leave_channel() -> str:
    """Remove the current user from the channel which name she/he has given in the POST form.
    Show appropriate message after leaving the channel. Set up the app again for this user.

    Returns:
        The redirection to the main page of the app.

    """
    channel_name = request.form.get("channel")
    channel_id = Channel.query.filter_by(name=channel_name).first().id

    leave_msg = f'You have successfully leaved the channel "{channel_name}!"'

    (db.session.query(ChannelAllowList).filter(ChannelAllowList.user_id == current_user.id)
                                       .filter(ChannelAllowList.channel_id == channel_id)
                                       .delete())

    if not ChannelAllowList.query.filter_by(channel_id=channel_id).first():
        db.session.delete(Channel.query.filter_by(id=channel_id).first())
        leave_msg += '</br>Since you have been the last user, the channel has been deleted.'

    db.session.commit()
    flash(Markup(leave_msg), 'success')
    return redirect(url_for('main.setup_app'))

@main.route('/is-admin', methods=['POST'])
@login_required
def is_admin_ajax():
    """Check if the current user is an admin of the channel which name has been given
    in the POST form. Return appropriate JSON as a response.

    Returns:
        JSON response to the AJAX caller.

    """
    channel_name = request.form.get('channelName')
    if not channel_name:
        return jsonify({'response': False})

    channel = Channel.query.filter_by(name=channel_name).first()

    if not channel:
        return jsonify({'response': False})

    return jsonify({'response': is_admin(channel, current_user)})

@main.route('/channel/<string:channel_name>', methods=['GET'])
@login_required
def channel_settings(channel_name: str) -> str:
    """Check if the current user can see the settings of the given channel.
    If she/he can, then generate the page with the settings of the given channel.

    Args:
        channel_name: Name of the channel which settings page should be generated.

    Returns:
        Template of the channel settings page if successful, otherwise redirection to the main page.

    """
    channel = Channel.query.filter_by(name=channel_name).first()

    if not channel:
        return no_channel()

    channel_permit = (ChannelAllowList.query.filter_by(user_id=current_user.id)
                                            .filter_by(channel_id=channel.id).first())

    if channel_permit and channel_permit.user_role == UserRole.ADMIN.value:

        num_users = get_number_of_channels_users(channel)
        num_messages = get_number_of_channels_messages(channel)
        users = get_channels_users(channel)

        only_admins = all([is_admin(channel, user) for user in users])
        user_tuples = [(user, is_admin(channel, user)) for user in users]

        return render_template(
            'settings-channel.html',
            channel=channel, num_users=num_users, num_messages=num_messages, user_tuples=user_tuples,
            only_admins=only_admins
        )

    else:
        return no_channel()

@main.route('/make-admin', methods=['POST'])
@login_required
def make_admin() -> str:
    """Take the POST form with parameters channel_id and user and make the given user
    admin of the given channel.

    Returns:
        The redirection to the settings of the channel.

    """
    channel_id = request.form.get('channel_id')
    user_id = request.form.get('user')
    return admin_manager(command='make', channel_id=channel_id, user_id=user_id)

@main.route('/revoke-admin', methods=['POST'])
@login_required
def revoke_admin():
    """Get user's an channel's ID from the POST form. Revoke the admin privileges of the user if possible.

    Returns:
        The redirection to the channel settings page with appropriate flash message.

    """
    channel_id = request.form.get('channel_id')
    user_id = request.form.get('user')
    return admin_manager(command='revoke', channel_id=channel_id, user_id=user_id)

@main.route('/remove-user', methods=['POST'])
@login_required
def remove_user() -> str:
    """Get user's an channel's ID from the POST form. Remove the user form the channel if possible.

    Returns:
        The redirection to the channel settings page with appropriate flash message.

    """
    channel_id = request.form.get('channel_id')
    user_id = request.form.get('user')

    checked_value = check_channel_settings_form(channel_id, user_id)

    if (not checked_value) or is_admin(Channel.query.get(channel_id), User.query.get(user_id)):
        flash("The user can't be removed.", 'danger')
        return redirect(url_for('main.setup_app'))
    else:
        channel, user = checked_value

    allow_record = (ChannelAllowList.query.filter_by(channel_id=channel.id)
                                          .filter_by(user_id=user.id).first())

    db.session.delete(allow_record)

    db.session.commit()
    flash(f"The user {user.username} has been removed from channel {channel.name}.", 'success')
    return redirect(f"channel/{channel.name}")
