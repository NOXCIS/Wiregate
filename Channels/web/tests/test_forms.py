"""Test the forms package."""

import pytest
from wtforms import StringField
from wtforms.validators import ValidationError

from app import app
from app.forms.channel import ChannelForm, AddChannelForm, UpdateChannelForm
from app.forms.registration import RegistrationForm
from app.forms.update_profile import UpdateProfileForm
from app.models import db, Channel, User

class TestChannelForms:
    @pytest.fixture
    def sample_channel(self) -> Channel:
        """Sample channel to be tested"""
        return Channel(name='test', password='password')

    @pytest.fixture
    def valid_field(self) -> StringField:
        """String Field of a valid name."""
        field = StringField()
        field.data = 'HE LL-o'
        return field

    @pytest.fixture
    def invalid_field(self) -> StringField:
        """String Field of an invalid name."""
        string_field = StringField()
        string_field.data = 'hello!'
        return string_field

    def test_invalid_name(self) -> None:
        assert ChannelForm._channel_has_invalid_name('')
        assert ChannelForm._channel_has_invalid_name(' leadingspace')
        assert ChannelForm._channel_has_invalid_name('trailingspace ')
        assert ChannelForm._channel_has_invalid_name('@=)(%^')
        assert ChannelForm._channel_has_invalid_name('this illegal @ char is in the middle')
        assert ChannelForm._channel_has_invalid_name(' ')
        assert ChannelForm._channel_has_invalid_name('Mytitle!')

    def test_valid_name(self) -> None:
        assert not ChannelForm._channel_has_invalid_name('legal channel')
        assert not ChannelForm._channel_has_invalid_name('a')
        assert not ChannelForm._channel_has_invalid_name('A')
        assert not ChannelForm._channel_has_invalid_name('AbcDeFgHiJkL')
        assert not ChannelForm._channel_has_invalid_name('a b c d e f g h i j k l m')
        assert not ChannelForm._channel_has_invalid_name('my_title')
        assert not ChannelForm._channel_has_invalid_name('my-title')

    def test_already_exist(self, sample_channel: Channel) -> None:
        with app.app_context():
            db.create_all()
            db.session.add(sample_channel)
            assert ChannelForm._channel_already_exists('test')
            assert not ChannelForm._channel_already_exists('another')

    def test_validators(self, valid_field: StringField, invalid_field: StringField) -> None:
        with app.app_context():
            db.create_all()

        with app.test_request_context():
            for form in (AddChannelForm(), UpdateChannelForm()):
                with pytest.raises(ValidationError):
                    form.validate_name(invalid_field)

                form.validate_name(valid_field)

                with app.app_context():
                    db.session.add(Channel(name=valid_field.data, password='password'))
                    with pytest.raises(ValidationError):
                        form.validate_name(valid_field)

class TestProfileForms:
    @pytest.fixture
    def sample_username(self) -> StringField:
        """Sample StringField of an username."""
        field = StringField()
        field.data = 'uSeRnAmE'
        return field

    @pytest.fixture
    def sample_email(self) -> StringField:
        """Sample StringField of an email."""
        field = StringField()
        field.data = 'python@mail.com'
        return field

    def test_validate_username(self, sample_username: StringField, sample_email: StringField) -> None:
        with app.app_context():
            db.create_all()

            with app.test_request_context():
                for form in (RegistrationForm(), UpdateProfileForm()):
                    db.session.rollback()
                    form.validate_username(sample_username)

                    db.session.add(User(
                        username='USERName', email=sample_email.data, password='password'
                    ))
                    with pytest.raises(ValidationError):
                        form.validate_username(sample_username)

    def test_validate_email(self, sample_username: StringField, sample_email: StringField) -> None:
        with app.app_context():
            db.create_all()

            with app.test_request_context():
                for form in (RegistrationForm(), UpdateProfileForm()):
                    db.session.rollback()
                    form.validate_email(sample_email)

                    db.session.add(User(
                        username=sample_username.data, email='PYTHON@mail.com', password='password'
                    ))
                    with pytest.raises(ValidationError):
                        form.validate_email(sample_email)
