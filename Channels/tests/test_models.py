"""Test the models package."""

from datetime import datetime

from app import app
from app.models import db, Channel, User, ChannelAllowList, Message
from app.models.channel_allowlist import UserRole


def test_repr() -> None:
    channel = Channel(name='channelName', password='pass')
    assert channel.__repr__() == "Channel(name='channelName')"

    user = User(username='userName', password='password', email='check@my.github')
    assert user.__repr__() == "User(name='userName')"

    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.add(user)
        db.session.add(channel)

        channel_id = Channel.query.first().id
        user_id = User.query.first().id

    channel_allow_list = ChannelAllowList(user_id=user_id, channel_id=channel_id, user_role=UserRole.ADMIN.value)
    assert channel_allow_list.__repr__() == \
        f'ChannelAllowList(channel_id=1, user_id=1, user_role={UserRole.ADMIN.value})'

    time = datetime.utcnow()
    message = Message(content='content', author_id=user_id, target_channel=channel_id, time=time)
    assert message.__repr__() == f"Message(author_id=1, target_channel=1, time={time})"
