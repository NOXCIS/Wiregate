"""
Module containing all custom CLI commands.
"""

from .bp import cli_bp
from app.models.base import db

@cli_bp.cli.command('create-db')
def create_db() -> None:
    """Create all models into databases."""
    db.create_all()
    print('All the databases were successfully created!')

@cli_bp.cli.command('drop-db')
def drop_db() -> None:
    """Drop all databases created from models."""
    db.drop_all()
    print('All the databases were successfully dropped!')
