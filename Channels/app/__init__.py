"""
This is the main package of the application.
This particular module contains the app factory and
"""

from flask import Flask
from flask_socketio import SocketIO, join_room, leave_room

from .config import configure_app
from . import models, main, login, api, bcrypt, login_manager, cli, schemas

from app.sockets import add_message
import app.cli.commands
from .models import Channel, Message, db


def create_app() -> Flask:
    """Flask app factory initialising all its components.

    Returns:
        The created Flask application.

    """
    app = Flask(__name__)
    configure_app(app)

    models.init_app(app)
    schemas.init_app(app)

    main.init_app(app)
    login.init_app(app)
    api.init_app(app)

    bcrypt.init_app(app)
    login_manager.init_app(app)
    cli.init_app(app)

    return app


app = create_app()
socket_io = SocketIO(app)


@socket_io.on('join room')
def join_r(data: dict) -> None:
    """Let the current user join the given room.

    Args:
        data: The dictionary with the name of the room.

    """
    room = data['room']
    join_room(room)

@socket_io.on('leave room')
def leave_r(data: dict) -> None:
    """Let the current user leave the given room.

    Args:
        data: The dictionary with the name of the room.

    """
    room = data['room']
    leave_room(room)

@socket_io.on('add message')
def add_message_socket(data: dict) -> None:
    """Add the received message to the database and show it dynamically in its room."""
    add_message(data)
