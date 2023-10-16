"""Test the main package"""

from datetime import datetime
from typing import Callable
import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from app import app
from app.models import db, User, Channel, Message, ChannelAllowList
from app.models.channel_allowlist import UserRole
from app.bcrypt.utils import hash_password

from tests.utils import login, decode_bytecode_single_quote
from tests.test_login import route_context


def channel_settings_context(func: Callable) -> Callable:
    """The decorator for the test of the routes for settings of a channel.

    Args:
        func: The function to be decorated.

    Returns:
        The decorated function.

    """
    @route_context
    def wrapper(*args, **kwargs) -> None:
        """Wrapper of the decorator."""
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        db.session.add(User(
            username='testUsername2', password=hash_password('testPassword2'), email='test2@email.com'
        ))
        db.session.add(Channel(name='channel', password='password'))
        db.session.add(ChannelAllowList(channel_id=1, user_id=1))
        func(*args, **kwargs)

    return wrapper

def get_driver() -> webdriver.Chrome:
    """Get the driver used by Selenium tests.

    Returns:
        The driver used by Selenium tests.

    """
    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    if os.environ.get('IS_DOCKER'):
        return webdriver.Chrome('/usr/bin/chromedriver', chrome_options=options)
    else:
        return webdriver.Chrome('tests/assets/local_webdriver/chromedriver', chrome_options=options)

def join_test_channel(driver: webdriver.Chrome, password: str) -> None:
    """Join the channel through the join channel form.

    Args:
        driver: The Chrome Webdriver used for testing.
        password: The password that should be filled in.

    """
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, 'join-channel-button'))
    )
    driver.find_element_by_id('join-channel-button').click()
    WebDriverWait(driver, 10).until(
        lambda x: x.find_element_by_name('join-name').is_displayed())
    driver.find_element_by_name('join-name').clear()
    driver.find_element_by_name('join-name').send_keys('testJoin')
    join_channel_password = driver.find_element_by_name('join-password')
    join_channel_password.send_keys(password)
    join_channel_password.send_keys(Keys.ENTER)


class TestRoutes:

    def test_setup_app(self) -> None:
        app.config['TESTING'] = True
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(Channel(name='testJoin', password=hash_password('passwordJoin')))
            db.session.commit()
            assert not User.query.first()

            driver = get_driver()
            time.sleep(5)
            # Registration
            driver.get('http://localhost:5000/register')

            login_input = WebDriverWait(driver, 10).until(
                lambda x: x.find_element_by_name('username'))
            login_input.send_keys('testUsername')

            driver.find_element_by_name('email').send_keys('test@email.com')
            driver.find_element_by_name('password').send_keys('testPassword')
            confirm_password = driver.find_element_by_name('confirm_password')
            confirm_password.send_keys('testPassword')
            confirm_password.send_keys(Keys.ENTER)
            assert 'An account was successfully created for testUsername!' in driver.page_source

            # Log in
            driver.find_element_by_name('email').send_keys('test@email.com')
            password_input = driver.find_element_by_name('password')
            password_input.send_keys('testPassword')
            password_input.send_keys(Keys.ENTER)
            assert 'Log out' in driver.page_source
            assert 'No channels so far' in driver.page_source

            # Add channel
            #   - passwords don't match
            time.sleep(1)
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'add-channel-button'))
            )
            driver.find_element_by_id('add-channel-button').click()
            WebDriverWait(driver, 10).until(
                lambda x: x.find_element_by_name('add-name').is_displayed())
            driver.find_element_by_name('add-name').send_keys('testChannel')
            driver.find_element_by_name('add-password').send_keys('testPassword')
            add_channel_conf_password = driver.find_element_by_name('add-confirm_password')
            add_channel_conf_password.send_keys('testPassword2')
            add_channel_conf_password.send_keys(Keys.ENTER)
            assert 'Passwords must match' in driver.page_source
            assert len(Channel.query.all()) == 1

            #   - passwords match
            WebDriverWait(driver, 10).until(
                lambda x: x.find_element_by_name('add-name').is_displayed())
            driver.find_element_by_name('add-password').send_keys('testPassword')
            add_channel_conf_password = driver.find_element_by_name('add-confirm_password')
            add_channel_conf_password.send_keys('testPassword')
            add_channel_conf_password.send_keys(Keys.ENTER)
            assert 'You have successfully added the channel "testChannel"' in driver.page_source
            assert len(Channel.query.all()) == 2

            # Join channel
            #   - invalid password
            join_test_channel(driver, 'passwordJoin2')
            assert 'Joining unsuccessful' in driver.page_source
            assert len(ChannelAllowList.query.all()) == 1

            #   - valid password
            join_test_channel(driver, 'passwordJoin')
            assert 'Joining unsuccessful' not in driver.page_source
            assert 'You have successfully joined the channel "testJoin"' in driver.page_source
            assert len(ChannelAllowList.query.all()) == 2

            #   - trying to re-join the channel
            join_test_channel(driver, 'passwordJoin')
            assert 'Joining unsuccessful' not in driver.page_source
            assert 'You have successfully joined the channel "testJoin"' not in driver.page_source
            assert 'You are already member of this channel' in driver.page_source
            assert len(ChannelAllowList.query.all()) == 2

            driver.close()
            time.sleep(5)
            driver.quit()
            assert User.query.first()

    @route_context
    def test_get_messages_ajax(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        db.session.add(Channel(name='channel', password='password'))

        with app.test_client() as c:
            rv = c.post('/get-messages', data={'channelName': 'channel'}, follow_redirects=True)
            assert 'messages' not in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            rv = c.post('/get-messages', data={'channelName': 'channel', 'counter': '1'}, follow_redirects=True)
            assert 'Fatal error' in str(rv.data)

            rv = c.post('/get-messages', data={'channelName': 'channel', 'counter': 'NotANumber'}, follow_redirects=True)
            assert 'Fatal error' in str(rv.data)

            rv = c.post('/get-messages', data={'channelName': 'channel', 'counter': '0'}, follow_redirects=True)
            assert 'Fatal error' not in str(rv.data)
            json = eval(rv.data.decode('utf8'))
            assert json['messages'] == []

            for _ in range(5):
                db.session.add(Message(content='_', target_channel=1, author_id=1, time=datetime.utcnow()))

            rv = c.post('/get-messages', data={'channelName': 'channel', 'counter': '3'}, follow_redirects=True)
            assert 'messages' in str(rv.data)
            json = eval(rv.data.decode('utf8'))
            assert len(json['messages']) == 3
            for content, user in [[message['content'], message['userName']] for message in json['messages']]:
                assert content == '_'
                assert user == 'testUsername'

            for _ in range(20):
                db.session.add(Message(content='&', target_channel=1, author_id=1, time=datetime.utcnow()))

            rv = c.post('/get-messages', data={'channelName': 'channel', 'counter': '25'}, follow_redirects=True)
            json = eval(rv.data.decode('utf8'))

            assert len([message['content'] for message in json['messages']]) == 20

            assert set([message['content'] for message in json['messages']]) == set('&')

    @route_context
    def test_get_initial_counter_ajax(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        db.session.add(Channel(name='channel', password='password'))

        with app.test_client() as c:
            rv = c.post('/get-messages', data={'channelName': 'channel'}, follow_redirects=True)
            assert 'counter' not in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            rv = c.post('/initial-counter', data={'channelName': 'channel'}, follow_redirects=True)
            assert 'counter' in str(rv.data)
            json = eval(rv.data.decode('utf8'))
            assert json['counter'] == 0

            for _ in range(20):
                db.session.add(Message(content='&', target_channel=1, author_id=1, time=datetime.utcnow()))

            rv = c.post('/initial-counter', data={'channelName': 'channel'}, follow_redirects=True)
            json = eval(rv.data.decode('utf8'))
            assert json['counter'] == 20

    @channel_settings_context
    def test_leave_channel(self) -> None:
        db.session.add(ChannelAllowList(channel_id=1, user_id=2))

        with app.test_client() as c:
            rv = c.post('/leave-channel', data={'channel': 'channel'}, follow_redirects=True)
            assert 'the channel' not in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            rv = c.post('/leave-channel', data={'channel': 'channel'}, follow_redirects=True)
            assert 'the channel' in str(rv.data)
            assert 'the last user' not in str(rv.data)

            assert len(ChannelAllowList.query.all()) == 1

        with app.test_client() as c:
            rv = login(c, 'test2@email.com', 'testPassword2')
            assert 'Log out' in str(rv.data)

            rv = c.post('/leave-channel', data={'channel': 'channel'}, follow_redirects=True)
            assert 'the channel' in str(rv.data)
            assert 'the last user' in str(rv.data)

            assert not ChannelAllowList.query.all()

    @route_context
    def test_is_admin_ajax(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        db.session.add(Channel(name='channel', password='password'))
        db.session.add(ChannelAllowList(channel_id=1, user_id=1))

        with app.test_client() as c:
            rv = c.post('/is-admin', data={'channelName': 'channel'}, follow_redirects=True)
            assert 'response' not in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            # User is not admin of the channel.
            rv = c.post('/is-admin', data={'channelName': 'channel'}, follow_redirects=True)
            assert 'response' in str(rv.data)

            json = eval(rv.data.decode('utf8').replace('false', 'False').replace('true', 'True'))
            assert not json['response']

            ChannelAllowList.query.first().user_role = UserRole.ADMIN.value

            # User is admin of the channel
            rv = c.post('/is-admin', data={'channelName': 'channel'}, follow_redirects=True)
            assert 'response' in str(rv.data)

            json = eval(rv.data.decode('utf8').replace('false', 'False').replace('true', 'True'))
            assert json['response']

            # No channel given in the form
            rv = c.post('/is-admin', follow_redirects=True)
            assert 'response' in str(rv.data)

            json = eval(rv.data.decode('utf8').replace('false', 'False').replace('true', 'True'))
            assert not json['response']

            # Channel given in the form doesn't exist
            rv = c.post('/is-admin', data={'channelName': 'channel_second'}, follow_redirects=True)
            assert 'response' in str(rv.data)

            json = eval(rv.data.decode('utf8').replace('false', 'False').replace('true', 'True'))
            assert not json['response']

    @route_context
    def test_channel_settings(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        db.session.add(Channel(name='channel', password='password'))
        db.session.add(ChannelAllowList(channel_id=1, user_id=1))

        with app.test_client() as c:
            rv = c.get('/channel/channel', follow_redirects=True)
            assert 'Please log in to access this page' in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            rv = c.get('/channel/channel', follow_redirects=True)
            assert 'Number of users:' not in str(rv.data)
            assert "you don't have necessary permission" in decode_bytecode_single_quote(rv.data)

            ChannelAllowList.query.first().user_role = UserRole.ADMIN.value

            rv = c.get('/channel/channel', follow_redirects=True)
            assert 'Number of users:' in str(rv.data)

            rv = c.get('/channel/channel_second', follow_redirects=True)
            assert 'Number of users:' not in str(rv.data)
            assert "channel doesn't exist" in decode_bytecode_single_quote(rv.data)

    @channel_settings_context
    def test_make_admin(self) -> None:
        with app.test_client() as c:
            rv = c.post('/make-admin', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert 'Please log in to access this page' in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            # The caller is not admin.
            rv = c.post('/make-admin', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "It wasn't possible to modify the role of the given user" in decode_bytecode_single_quote(rv.data)

            ChannelAllowList.query.filter_by(user_id=1).first().user_role = UserRole.ADMIN.value

            # The caller is admin but the nominated user is not allowed to be in the channel.
            rv = c.post('/make-admin', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "It wasn't possible to modify the role of the given user" in decode_bytecode_single_quote(rv.data)

            # The caller is admin and the nominated user can see the channel
            db.session.add(ChannelAllowList(channel_id=1, user_id=2))
            rv = c.post('/make-admin', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "It wasn't possible to modify the role of the given user" not in decode_bytecode_single_quote(rv.data)
            assert ChannelAllowList.query.filter_by(user_id=2).first().user_role == UserRole.ADMIN.value

    @channel_settings_context
    def test_revoke_admin(self) -> None:
        with app.test_client() as c:
            rv = c.post('/revoke-admin', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert 'Please log in to access this page' in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            # The caller is not admin.
            rv = c.post('/revoke-admin', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "It wasn't possible to modify the role of the given user" in decode_bytecode_single_quote(rv.data)

            ChannelAllowList.query.filter_by(user_id=1).first().user_role = UserRole.ADMIN.value

            # The caller is admin but the nominated user is not allowed to be in the channel.
            rv = c.post('/revoke-admin', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "It wasn't possible to modify the role of the given user" in decode_bytecode_single_quote(rv.data)

            # The caller is admin, the nominated user can see the channel
            db.session.add(ChannelAllowList(channel_id=1, user_id=2, user_role=UserRole.ADMIN.value))
            rv = c.post('/revoke-admin', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "It wasn't possible to modify the role of the given user" not in decode_bytecode_single_quote(rv.data)
            assert ChannelAllowList.query.filter_by(user_id=2).first().user_role == UserRole.NORMAL_USER.value

    @channel_settings_context
    def test_remove_user(self) -> None:
        db.session.add(ChannelAllowList(channel_id=1, user_id=2, user_role=UserRole.ADMIN.value))
        with app.test_client() as c:
            rv = c.post('/remove-user', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert 'Please log in to access this page' in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            # The caller is not admin.
            rv = c.post('/remove-user', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "The user can't be removed" in decode_bytecode_single_quote(rv.data)

            # The caller is admin but so is the second user.
            ChannelAllowList.query.filter_by(user_id=1).first().user_role = UserRole.ADMIN.value
            rv = c.post('/remove-user', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "The user can't be removed" in decode_bytecode_single_quote(rv.data)
            assert ChannelAllowList.query.filter_by(user_id=2).first()

            # The caller is admin but the second user is not.
            ChannelAllowList.query.filter_by(user_id=2).first().user_role = UserRole.NORMAL_USER.value
            rv = c.post('/remove-user', data={'channel_id': 1, 'user': 2}, follow_redirects=True)
            assert "The user can't be removed" not in decode_bytecode_single_quote(rv.data)
            assert not ChannelAllowList.query.filter_by(user_id=2).first()
