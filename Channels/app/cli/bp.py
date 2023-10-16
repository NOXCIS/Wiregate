"""
Module containing the blueprint for the command line interface.
"""

from flask import Blueprint

cli_bp = Blueprint('cli_bp', __name__, cli_group=None)
