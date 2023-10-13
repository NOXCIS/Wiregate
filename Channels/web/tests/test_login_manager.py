"""Test the login_manager package."""

from app import app
from app.models import db, User
from app.login_manager import load_user

def test_get_user():
    with app.app_context():
        db.drop_all()
        db.create_all()

        first_user = User(username='name', email='python@mail.com', password='pass')
        second_user = User(username='noname', email='ilove@python.com', password='test')

        db.session.add(first_user)
        db.session.add(second_user)

        assert load_user('1') == first_user
        assert load_user('2') == second_user
        assert load_user('1').username == 'name'
