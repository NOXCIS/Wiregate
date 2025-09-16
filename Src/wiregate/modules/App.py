from flask import Flask, make_response
import secrets
import os
from datetime import timedelta

from .ConfigEnv import SECURE_SESSION, DASHBOARD_MODE

# Create Flask app
app = Flask("WireGate", template_folder=os.path.abspath("./static/app/dist"))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 5206928
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = secrets.token_urlsafe(420)
app.permanent_session_lifetime = timedelta(hours=1)

# Security configurations
app.config['SESSION_COOKIE_SECURE'] = SECURE_SESSION and DASHBOARD_MODE == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'wiregate:'


from .ConfigEnv import (
    DASHBOARD_VERSION,
    CONFIGURATION_PATH,
    DB_PATH
)

# Create DB directory if it doesn't exist
if not os.path.isdir(DB_PATH):
    os.mkdir(DB_PATH)


def ResponseObject(status=True, message=None, data=None):
    response = make_response({
        "status": status,
        "message": message,
        "data": data
    })
    response.content_type = "application/json"
    return response









