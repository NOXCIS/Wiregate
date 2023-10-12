#!venv/bin/python
import os
import unittest

from config import basedir
from app import app, db
from app.models import User, Message


class TestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'test.db')
        self.app = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_change_password(self):
        u = User(username='toto')
        u.set_password('bla')
        self.assertFalse(u.check_password('bli'))
        self.assertTrue(u.check_password('bla'))

    def test_delete_existing(self):
        self.assertTrue(User.create('foobar3','foobar3'))
        self.assertTrue(User.delete('foobar3'))

    def test_delete_non_existing(self):
        self.assertTrue(User.create('foobar4','foobar4'))
        self.assertFalse(User.delete('foobar44'))
        self.assertTrue(User.delete('foobar4'))

    def test_delete_after_posting(self):
        self.assertTrue(User.create('foobar5', 'foobar5'))
        self.assertTrue(Message.create(User.find('foobar5'),'hello'))
        self.assertTrue(User.delete('foobar5'))

if __name__ == '__main__':
    unittest.main()