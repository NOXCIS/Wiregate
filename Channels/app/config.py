"""
Module containing settings of the app.
"""

from os import environ
from flask import Flask
import secrets
import string

def configure_app(app: Flask) -> None:
    """Set the internal settings of the app.

    Args:
        app: Flask application to be configured.

    """



    characters = string.ascii_letters + string.digits + string.punctuation
    appkey = ''.join(secrets.choice(characters) for _ in range(4200))
    #wg_dash_appkey = os.environ.get('WG_DASH_SECRET_KEY')
    app.secret_key = appkey

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE_URI']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config["JSON_SORT_KEYS"] = False
