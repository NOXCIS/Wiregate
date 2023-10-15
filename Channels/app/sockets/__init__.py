"""
This package contains helper methods used by web sockets of the app.
"""

from datetime import datetime

from flask import url_for
from flask_socketio import emit
from flask_login import current_user

from app.main.utils import convert_time_to_string
from app.models import db, Channel, Message


def add_message(data: dict) -> None:
    """Add message to database and show it dynamically.

    Args:
        data: The dictionary containing the channel name and content of the message.

    """
    channel = data['channel']
    message_content = data['message_content']

    username = current_user.username
    user_id = current_user.id
    user_picture = f"{url_for('static', filename='img/profile_pictures')}/{ current_user.profile_picture }"

    full_time = datetime.utcnow()

    channel_id = Channel.query.filter_by(name=channel).first().id

    db.session.add(Message(
        content=message_content, author_id=user_id, time=full_time, target_channel=channel_id
    ))

    db.session.commit()

    return announce_message(username, user_picture, convert_time_to_string(full_time), channel, message_content)

def announce_message(user_name: str, user_picture: str, time: str, channel: str, message_content: str) -> None:
    """Emit all information about the message that was added to DB.

    Args:
        user_name: Name of the user who sent the message.
        user_picture: Picture of the user who sent the message.
        time: Time when she/he sent it.
        channel: Channel the message was sent to.
        message_content: Content of the message.

    """
    response = {
        'userName': user_name,
        'userPicture': user_picture,
        'time': time,
        'channel': channel,
        'messageContent': message_content
    }
    emit('announce message', response, room=channel)