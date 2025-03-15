from flask import Flask, make_response
import secrets
import os
import sqlite3
from datetime import timedelta

# Create Flask app
app = Flask("WireGate", template_folder=os.path.abspath("./static/app/dist"))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 5206928
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = secrets.token_urlsafe(420)
app.permanent_session_lifetime = timedelta(hours=1)


def ResponseObject(status=True, message=None, data=None):
    response = make_response({
        "status": status,
        "message": message,
        "data": data
    })
    response.content_type = "application/json"
    return response









