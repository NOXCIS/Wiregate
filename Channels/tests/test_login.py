"""Test the login package."""

import pytest
from datetime import datetime
import os
from PIL import Image
from werkzeug.datastructures import FileStorage
from typing import Callable

import app.login.utils as u
from tests.utils import login, find_substr_between

from app import app
from app.models import db, User, Message, Channel, ChannelAllowList

from app.forms.registration import RegistrationForm
from app.forms.login import LoginForm

from app.bcrypt.utils import check_hashed_password, hash_password

def route_context(func: Callable) -> Callable:
    """Decorator used for testing the routes.

    Args:
        func: The function to be decorated.

    Returns:
        The decorated function.

    """
    def wrapper(*args, **kwargs) -> None:
        """Wrapper of the decorator."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            func(*args, **kwargs)
    return wrapper

class TestUtils:

    @pytest.fixture
    def user_1(self) -> User:
        """Sample user for testing."""
        return User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        )

    @pytest.fixture
    def user_2(self) -> User:
        """Another sample user for testing."""
        return User(
            username='testUsername2', password=hash_password('testPassword2'), email='test2@email.com'
        )

    @pytest.fixture
    def channel_to_test(self) -> Channel:
        """Sample channel for testing."""
        return Channel(name='testChannel', password='testPassword')

    @route_context
    def test_add_user(self) -> None:
        username = 'testUsername'
        password = 'testPassword'
        email = 'test@email.com'

        with app.test_request_context():
            form = RegistrationForm()
            form.username.data = username
            form.password.data = password
            form.email.data = email

            u.add_user(form)

        user = User.query.first()
        assert user.username == username
        assert user.email == email
        assert check_hashed_password(user.password, password)

    def test_is_valid_user(self, user_1, user_2) -> None:
        with app.test_request_context():
            form = LoginForm()
            form.email.data = 'test@email.com'
            form.password.data = 'testPassword'

        assert u.is_valid_user(user_1, form)
        assert not u.is_valid_user(user_2, form)
        assert not u.is_valid_user(None, form)

    def test_get_number_of_all_messages(self, user_1, user_2, channel_to_test) -> None:
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(user_1)
            db.session.add(user_2)
            db.session.add(channel_to_test)
            with app.test_client() as c:
                rv = login(c, user_1.email, 'testPassword')
                assert 'Log out' in str(rv.data)
                assert u.get_number_of_all_messages() == 0
                db.session.add(Message(content='_', time=datetime.utcnow(), author_id=1, target_channel=1))
                assert u.get_number_of_all_messages() == 1

                for _ in range(10):
                    db.session.add(Message(content='_', time=datetime.utcnow(), author_id=2, target_channel=1))

                assert u.get_number_of_all_messages() == 1

            with app.test_client() as c:
                rv = login(c, user_2.email, 'testPassword')
                assert 'Log out' not in str(rv.data)
                rv = login(c, user_2.email, 'testPassword2')
                assert 'Log out' in str(rv.data)
                assert u.get_number_of_all_messages() == 10

    def test_get_number_of_all_channels(self, user_1, user_2, channel_to_test) -> None:
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(user_1)
            db.session.add(user_2)
            db.session.add(channel_to_test)
            with app.test_client() as c:
                rv = login(c, user_1.email, 'testPassword')
                assert 'Log out' in str(rv.data)
                assert u.get_number_of_all_channels() == 0
                db.session.add(ChannelAllowList(user_id=1, channel_id=1))
                assert u.get_number_of_all_channels() == 1

            with app.test_client() as c:
                rv = login(c, user_2.email, 'testPassword')
                assert 'Log out' not in str(rv.data)
                rv = login(c, user_2.email, 'testPassword2')
                assert 'Log out' in str(rv.data)
                assert u.get_number_of_all_channels() == 0
                db.session.add(ChannelAllowList(user_id=2, channel_id=1))
                assert u.get_number_of_all_channels() == 1

    def test_update_user(self, user_1, user_2):
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(user_1)
            db.session.add(user_2)
            with app.test_client() as c:
                rv = login(c, user_1.email, 'testPassword')
                assert 'Log out' in str(rv.data)
                assert user_1.username == 'testUsername'
                assert user_1.email == 'test@email.com'
                assert user_2.username == 'testUsername2'
                assert user_2.email == 'test2@email.com'

                u.update_user('testUsername3', 'test3@email.com')
                assert user_1.username == 'testUsername3'
                assert user_1.email == 'test3@email.com'
                assert user_2.username == 'testUsername2'
                assert user_2.email == 'test2@email.com'

    def test_remove_old_profile_picture(self, user_1) -> None:
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(user_1)
            with app.test_client() as c:
                _ = login(c, user_1.email, 'testPassword')
                file = 'default.png'
                assert os.path.exists(u.get_profile_picture_full_path(file))

                new_file = 'test.png'
                new_absolute_path = u.get_profile_picture_full_path(new_file)
                assert not os.path.exists(new_absolute_path)

                with open(new_absolute_path, 'w') as _:
                    pass

                assert os.path.exists(new_absolute_path)

                User.query.first().profile_picture = new_file
                u.remove_old_profile_picture()
                assert not os.path.exists(new_absolute_path)

    def test_make_square(self) -> None:
        image = Image.new('RGB', (500, 500), (0, 0, 0, 0))
        new_image = u.make_square(image)
        assert new_image.size == (125, 125)
        assert new_image.getpixel((0, 0)) == (0, 0, 0)
        assert new_image.getpixel((36, 89)) == (0, 0, 0)
        assert new_image.getpixel((124, 124)) == (0, 0, 0)

        image = Image.new('RGB', (105, 65), (0, 0, 0, 0))
        new_image = u.make_square(image)
        assert new_image.size == (125, 125)
        assert new_image.getpixel((0, 0)) == (255, 255, 255)

        assert new_image.getpixel((9, 29)) == (255, 255, 255)
        assert new_image.getpixel((10, 30)) == (0, 0, 0)

        assert new_image.getpixel((114, 29)) == (255, 255, 255)
        assert new_image.getpixel((114, 30)) == (0, 0, 0)

        assert new_image.getpixel((94, 29)) == (255, 255, 255)
        assert new_image.getpixel((93, 30)) == (0, 0, 0)

    def test_save_profile_picture(self) -> None:
        directory = os.path.dirname(u.get_profile_picture_full_path('default.png'))
        assert len(os.listdir(directory)) == 1

        filenames = []
        with open('tests/assets/test.jpg', 'rb') as fp:
            file = FileStorage(fp)
            filename = u.save_profile_picture(file)
            filenames.append(filename)
            assert len(os.listdir(directory)) == 2

            for _ in range(5):
                filename = u.save_profile_picture(file)
                filenames.append(filename)

        assert len(os.listdir(directory)) == 7

        for full_filename in map(u.get_profile_picture_full_path, filenames):
            os.remove(full_filename)
        assert len(os.listdir(directory)) == 1

class TestRoutes:

    @route_context
    def test_index(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        with app.test_client() as c:
            rv = c.get('/', follow_redirects=True)
            assert 'Log out' not in str(rv.data)
            assert 'Log In' in str(rv.data)

            rv = login(c, 'incorrect@email.com', 'incorrectPassword')
            assert 'Login Unsuccessful. Incorrect email or password' in str(rv.data)
            assert 'Log out' not in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Login Unsuccessful. Incorrect email or password' not in str(rv.data)
            assert 'Log out' in str(rv.data)

            rv = c.get('/', follow_redirects=True)
            assert 'Log out' in str(rv.data)

    @route_context
    def test_register(self) -> None:
        with app.test_client() as c:
            rv = c.get('/register', follow_redirects=True)
            assert 'Register' in str(rv.data)
            assert 'Log In' not in str(rv.data)

            rv = c.post('/register', follow_redirects=True,
                        data=dict(
                            username='username', password='password', confirm_password='password',
                            email='sample@email.com'
                        ))
            assert 'An account was successfully created for username!' in str(rv.data)
            assert User.query.filter_by(username='username').first()

            rv = c.post('/register', follow_redirects=True,
                        data=dict(
                            username='username', password='password', confirm_password='pasword',
                            email='sampleemail.com'
                        ))
            assert 'This username is taken' in str(rv.data)
            assert 'Invalid email address' in str(rv.data)
            assert 'Passwords must match' in str(rv.data)
            assert User.query.count() == 1

    @route_context
    def test_logout(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))
        with app.test_client() as c:
            rv = c.get('/log-out', follow_redirects=True)
            assert 'Please log in to access this page' in str(rv.data)

            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)

            rv = c.get('/log-out', follow_redirects=True)
            assert 'Please log in to access this page' not in str(rv.data)
            assert 'Log out' not in str(rv.data)
            assert 'Log in' in str(rv.data)

    @route_context
    def test_settings(self) -> None:
        db.session.add(User(
            username='testUsername', password=hash_password('testPassword'), email='test@email.com'
        ))

        with app.test_client() as c:
            rv = login(c, 'test@email.com', 'testPassword')
            assert 'Log out' in str(rv.data)
            rv = c.get('/settings', follow_redirects=True)
            assert 'test@email.com' in find_substr_between(str(rv.data), 'Email address:', '</span>')
            assert 'default.png' in find_substr_between(str(rv.data), '<img src="', '"')
            assert '0' in find_substr_between(str(rv.data), 'All channels:', '</span>')
            assert '0' in find_substr_between(str(rv.data), 'All messages:', '</span>')

            db.session.add(Channel(name='channel', password='password'))
            db.session.add(ChannelAllowList(user_id=1, channel_id=1))
            rv = c.get('/settings', follow_redirects=True)
            assert '1' in find_substr_between(str(rv.data), 'All channels:', '</span>')
            assert '0' in find_substr_between(str(rv.data), 'All messages:', '</span>')

            for _ in range(13):
                db.session.add(Message(content='_', time=datetime.utcnow(), target_channel=1, author_id=1))

            rv = c.get('/settings', follow_redirects=True)
            assert '1' in find_substr_between(str(rv.data), 'All channels:', '</span>')
            assert '13' in find_substr_between(str(rv.data), 'All messages:', '</span>')

            rv = c.post('/settings', data=dict(username='anotherOne', email='new@email.com'), follow_redirects=True)
            assert 'Your profile has been successfully updated' in str(rv.data)
            assert 'new@email.com' in find_substr_between(str(rv.data), 'Email address:', '</span>')

            with open('tests/assets/test.jpg', 'rb') as fp:
                file = FileStorage(fp)
                rv = c.post('/settings', follow_redirects=True,
                            data=dict(username='anotherOne', email='new@email.com', profile_picture=file))

                assert 'Your profile has been successfully updated' in str(rv.data)
                assert 'default.png' not in find_substr_between(str(rv.data), '<img src="', '"')

                directory = os.path.dirname(u.get_profile_picture_full_path('default.png'))
                profile_pictures = os.listdir(directory)
                assert len(profile_pictures) == 2

                for profile_picture in profile_pictures:
                    if profile_picture != 'default.png':
                        os.remove(u.get_profile_picture_full_path(profile_picture))
