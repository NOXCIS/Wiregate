"""
Utility functions for API routes.
"""

from flask import request, abort

from app.models import User


def check_token() -> str:
    token = request.values.get('token')
    if not token:
        abort(404, description='Token not found.')
    else:
        return token

def check_user(token: str) -> User:
    user = User.verify_api_token(token)
    if not user:
        abort(403, description='The token is either invalid or expired.')
    else:
        return user
