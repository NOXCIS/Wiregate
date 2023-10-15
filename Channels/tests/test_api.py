"""Test the API package."""

from datetime import datetime
import json

from app import app
from app.bcrypt.utils import hash_password
from app.models import db, User, Message, Channel, ChannelAllowList

from tests.test_login import route_context
from tests.utils import login


class TestRoutes:

    @route_context
    def test_settings(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        with app.test_client() as c:
            rv = c.get('/api/settings', follow_redirects=True)
            assert 'Please log in to access this page' in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            rv = c.get('/api/settings', follow_redirects=True)
            assert 'Your API token is:' in str(rv.data)

    @route_context
    def test_channels(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        db.session.add(Channel(name='channel', password=hash_password('pass')))
        db.session.add(ChannelAllowList(user_id=1, channel_id=1))
        db.session.add(Message(content='hello world', time=datetime.utcnow(), author_id=1, target_channel=1))

        token = User.query.get(1).generate_api_token()

        with app.test_client() as c:
            rv = c.post('/api/channels', follow_redirects=True)
            assert rv.status_code == 404
            assert 'Token not found' in str(rv.data)

            rv = c.post('/api/channels', data=dict(token='invalid'), follow_redirects=True)
            assert rv.status_code == 403
            assert 'The token is either invalid or expired' in str(rv.data)

            rv = c.post('/api/channels', data=dict(token=token), follow_redirects=True)
            assert rv.status_code == 200
            json_res = json.loads(rv.data.decode('utf8'))
            channel_res = json_res[0]
            assert channel_res['name'] == 'channel'
            assert len(channel_res['allowed_users']) == 1
            assert len(channel_res['messages']) == 1

            message = channel_res['messages'][0]
            assert message['author']['username'] == 'testUsername'
            assert message['content'] == 'hello world'

    @route_context
    def test_channel(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        db.session.add(Channel(name='channel', password=hash_password('pass')))
        db.session.add(ChannelAllowList(user_id=1, channel_id=1))
        db.session.add(Channel(name='channel other', password=hash_password('pass')))

        token = User.query.get(1).generate_api_token()

        with app.test_client() as c:
            rv = c.post('/api/channels/channel', follow_redirects=True)
            assert rv.status_code == 404
            assert 'Token not found' in str(rv.data)

            rv = c.post('/api/channels/channel', data=dict(token='invalid'), follow_redirects=True)
            assert rv.status_code == 403
            assert 'The token is either invalid or expired' in str(rv.data)

            rv = c.post('/api/channels/channel', data=dict(token=token), follow_redirects=True)
            assert rv.status_code == 200
            json_res = json.loads(rv.data.decode('utf8'))
            assert json_res['name'] == 'channel'

            rv = c.post('/api/channels/channel other', data=dict(token=token), follow_redirects=True)
            assert rv.status_code == 404
            assert 'you do not have permission' in str(rv.data)

            rv = c.post('/api/channels/this does not exist', data=dict(token=token), follow_redirects=True)
            assert rv.status_code == 404
            assert 'does not exist' in str(rv.data)
