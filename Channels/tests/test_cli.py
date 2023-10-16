"""Test the CLI package."""

import pytest

from flask.testing import FlaskCliRunner
from sqlalchemy.exc import ProgrammingError

from app import app
from app.models import Channel

@pytest.fixture
def runner() -> FlaskCliRunner:
    """CLI runner for Flask."""
    return app.test_cli_runner()

def test_create_cmd(runner: FlaskCliRunner) -> None:
    with app.app_context():
        result = runner.invoke(args=['create-db'])
        assert 'created' in result.output
        Channel.query.all()

def test_drop_cmd(runner: FlaskCliRunner) -> None:
    with app.app_context():
        result = runner.invoke(args=['drop-db'])
        assert 'dropped' in result.output

        with pytest.raises(ProgrammingError):
            Channel.query.all()
