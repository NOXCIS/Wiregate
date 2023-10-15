"""
Module containing settings of the app.
"""

from os import environ
from flask import Flask

def configure_app(app: Flask) -> None:
    """Set the internal settings of the app.

    Args:
        app: Flask application to be configured.

    """
    app.secret_key = environ['SECRET_KEY']
    #app.secret_key = 'ed215f114bd528c0870a9c4900c69a1e'
    app.config['SESSION_TYPE'] = 'filesystem'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = environ['DATABASE_URI']
    #app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@db:5432/db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config["JSON_SORT_KEYS"] = False
