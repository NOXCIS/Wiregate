"""
Utility functions making use of bcrypt.
"""

from .base import bcrypt

def hash_password(password: str) -> str:
    """Get hashed password.

    Args:
        password: Password to be hashed.

    Returns:
        Hashed password.

    """
    hashed_password: str = bcrypt.generate_password_hash(password).decode('utf-8')
    return hashed_password


def check_hashed_password(hashed_password: str, password: str) -> bool:
    """Check if the hashed password is equivalent to the candidate password.

    Args:
        hashed_password: The hash to be compared against.
        password: The password to compare.

    Returns:
        True if two passwords are the same, False otherwise.

    """
    matching: bool = bcrypt.check_password_hash(hashed_password, password)
    return matching
