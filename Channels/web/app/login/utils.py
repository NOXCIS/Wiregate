"""
Utility functions for login routes.
"""

from secrets import token_hex
from os import path, remove
from PIL import Image

from flask_login import current_user

from typing import Optional, Final
from werkzeug.datastructures import FileStorage

from app.path import APP_PATH
from app.bcrypt.utils import hash_password, check_hashed_password

from app.forms.registration import RegistrationForm
from app.forms.login import LoginForm

from app.models import db, ChannelAllowList, Message

from app.models.user import User, DEFAULT_PROFILE_PICTURE

IMAGE_SIDE_SIZE: Final = 125

def add_user(form: RegistrationForm) -> None:
    """Add user (whose data is given in the registration form) to the database.

    Args:
        form: The filled registration form.

    """
    hashed_password = hash_password(form.password.data)
    db.session.add(User(
        username=form.username.data, email=form.email.data, password=hashed_password
    ))
    db.session.commit()


def is_valid_user(user: Optional[User], form: LoginForm) -> bool:
    """Check if the given user exists and then check if the password provided in the login form
    matches this user's password in the database.

    Args:
        user: None or the user in the database.
        form: The filled login form.

    Returns:
        True if the user is valid, false otherwise.

    """
    if isinstance(user, User):
        return check_hashed_password(user.password, form.password.data)
    else:
        return False

def get_number_of_all_messages() -> int:
    """Get the number of all channels that the current user has sent.

    Returns:
        The number of all messages of the user.

    """
    number_of_all_messages: int = Message.query.filter_by(author_id=current_user.id).count()
    return number_of_all_messages

def get_number_of_all_channels() -> int:
    """Get the number of all channels of the current user.

    Returns:
        The number of all channels.

    """
    number_of_all_channels: int = ChannelAllowList.query.filter_by(user_id=current_user.id).count()
    return number_of_all_channels

def update_user(username: str, email: str) -> None:
    """Update the current user setting her/him the given username and email.
    Commit all the changes to database, including the change of the profile picture.

    Args:
        username: The new username of the current user.
        email: The new email of the current user.

    """
    current_user.username = username
    current_user.email = email
    db.session.commit()

def get_profile_picture_full_path(profile_picture_filename: str) -> str:
    """Get the full path of the profile picture from the given relative path.

    Args:
        profile_picture_filename: The relative path to the profile picture.

    Returns:
        The full path to the profile picture.

    """
    return path.join(APP_PATH, 'app', 'static', 'img', 'profile_pictures', profile_picture_filename)

def remove_old_profile_picture() -> None:
    """Remove the profile picture of the current user."""
    if current_user.profile_picture != DEFAULT_PROFILE_PICTURE:
        old_profile_picture_path = get_profile_picture_full_path(current_user.profile_picture)
        remove(old_profile_picture_path)

def make_square(image: Image) -> Image:
    """Make the given picture a square picture.
    The blank pixels are filled with white.

    Args:
        image: Image to be transformed to a square image.

    Returns:
        The transformed square image.

    """
    x, y = image.size
    fill_color = (255, 255, 255, 0)  # white
    new_image = Image.new('RGB', (IMAGE_SIDE_SIZE, IMAGE_SIDE_SIZE), fill_color)
    new_image.paste(image, (int((IMAGE_SIDE_SIZE - x) / 2), int((IMAGE_SIDE_SIZE - y) / 2)))
    return new_image

def save_profile_picture(picture: FileStorage) -> str:
    """Save the given profile picture on the server and returns its relative path.
    The root directory is the one where all profile pictures are stored.
    The change is committed to the DB in update_user function.

    Args:
        picture: The profile picture to be saved.

    Returns:
        The relative path to the profile picture.

    """
    random_hex = token_hex(8)
    _, file_extension = path.splitext(picture.filename)  # type: ignore
    assert isinstance(file_extension, str)  # for Mypy type checking
    picture_filename = random_hex + file_extension
    picture_path = get_profile_picture_full_path(picture_filename)

    output_size = (IMAGE_SIDE_SIZE, IMAGE_SIDE_SIZE)
    image = Image.open(picture)
    image.thumbnail(output_size)

    square_image = make_square(image)
    square_image.save(picture_path)

    return picture_filename
