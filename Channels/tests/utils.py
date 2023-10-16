"""Utility functions used for unit tests."""

from flask import Response
from flask.testing import FlaskClient

def login(client: FlaskClient, email: str, password: str) -> Response:
    """Log in the user inside the test client.

    Args:
        client: The Flask Client where all the route testing happens in.
        email: The email that will be filled in the login form.
        password: The password that will be filled in the login form.

    Returns:
        The HTML response returned after logging in.

    """
    return client.post('/', data=dict(
        email=email,
        password=password
    ), follow_redirects=True)


def find_substr_between(full_str: str, left_substr: str, right_substr: str) -> str:
    """Find the substring between two other substrings in the given string.

    Args:
        full_str: The full string where substrings are contained in.
        left_substr: The substring from the left. (first occurrence)
        right_substr: The substring from the right. (first occurrence)

    Returns:
        The substring between the left and right substrings.

    Examples:
        >>> find_substr_between('aaabbbcccddddddbbb', 'bbb', 'ddd')
        'ccc'
    """
    return (full_str.split(left_substr))[1].split(right_substr)[0]

def decode_bytecode_single_quote(bytecode: bytes) -> str:
    """Decode bytecode to string and fix single quote.

    Args:
        bytecode: The bytecode to be decoded.

    Returns:
        The decoded bytecode.

    """
    return bytecode.decode("utf8").replace("&#39;", "'")
