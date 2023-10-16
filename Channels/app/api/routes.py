"""
All routes of the "API" blueprint.
"""

from flask import render_template, jsonify, Response, abort
from flask_login import login_required, current_user
from app.models import Channel
from app.schemas import ChannelSchema

from .base import api
from .utils import check_token, check_user


@api.route('/api/settings')
@login_required
def settings() -> Response:
    """Generate API settings page for the user with

    Returns:
        The API settings page with the generated token.

    """
    token = current_user.generate_api_token()
    return render_template('settings-api.html', token=token)

@api.route('/api/channels', methods=['POST'])
def show_channels() -> Response:
    token = check_token()
    user = check_user(token)

    channels = [
        Channel.query.get(allowed_record.channel_id)
        for allowed_record in user.allowed_channels
    ]
    channel_schema = ChannelSchema()
    return jsonify(channel_schema.dump(channels, many=True))

@api.route('/api/channels/<string:name>', methods=['POST'])
def show_channel(name: str) -> Response:
    token = check_token()
    user = check_user(token)

    channel = [
        Channel.query.get(allowed_record.channel_id)
        for allowed_record in user.allowed_channels
        if Channel.query.get(allowed_record.channel_id).name == name
    ]

    if not channel:
        abort(404, description=f'The channel {name} either does not exist or you do not have permission to see it.')
    else:
        channel = channel[0]
    channel_schema = ChannelSchema()
    return jsonify(channel_schema.dump(channel))
