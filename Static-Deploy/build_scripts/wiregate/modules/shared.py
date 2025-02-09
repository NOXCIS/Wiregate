from flask import Flask, make_response
import secrets
import os
import sqlite3
from datetime import datetime

# Create Flask app
app = Flask("WGDashboard", template_folder=os.path.abspath("./static/app/dist"))
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 5206928
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = secrets.token_urlsafe(420)

from . config import (
    DASHBOARD_VERSION,
    CONFIGURATION_PATH,
    DB_PATH
)



# Create DB directory if it doesn't exist
if not os.path.isdir(DB_PATH):
    os.mkdir(DB_PATH)

# Database connection
sqldb = sqlite3.connect(os.path.join(CONFIGURATION_PATH, 'db', 'wgdashboard.db'), check_same_thread=False)
sqldb.row_factory = sqlite3.Row
cursor = sqldb.cursor()

def ResponseObject(status=True, message=None, data=None):
    response = make_response({
        "status": status,
        "message": message,
        "data": data
    })
    response.content_type = "application/json"
    return response


def get_timestamped_filename():
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    return f'./log/access_{timestamp}.log'


def sqlSelect(statement: str, paramters: tuple = ()) -> sqlite3.Cursor:
    with sqldb:
        try:
            cursor = sqldb.cursor()
            return cursor.execute(statement, paramters)

        except sqlite3.OperationalError as error:
            print("[WGDashboard] SQLite Error:" + str(error) + " | Statement: " + statement)
            return []


def sqlUpdate(statement: str, paramters: tuple = ()) -> sqlite3.Cursor:
    with sqldb:
        cursor = sqldb.cursor()
        try:
            statement = statement.rstrip(';')
            s = f'BEGIN TRANSACTION;{statement};END TRANSACTION;'
            cursor.execute(statement, paramters)
            sqldb.commit()
        except sqlite3.OperationalError as error:
            print("[WGDashboard] SQLite Error:" + str(error) + " | Statement: " + statement)





