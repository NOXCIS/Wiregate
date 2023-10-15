"""
This package is responsible for login manager integration.
This particular module contains Login Manager initialization with user loading.
"""

from flask import Flask
from typing import Optional

from .base import login_manager
from app.models.user import User

def init_app(app: Flask) -> None:
    """Initialize Login Manager in the app.

    Args:
        app: Flask application where Login Manager should be work in.

    """
    login_manager.init_app(app)
    login_manager.login_view = 'login.index'
    login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    """Let the login manager load the user of the given id if she/he exists.

    Args:
        user_id: Id of the candidate user to be loaded in.

    Returns:
        The loaded user or None.

    """
    user: Optional[User] = User.query.get(int(user_id))
    return user
