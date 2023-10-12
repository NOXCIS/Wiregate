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

    def test_post_existing_user(self):
        self.assertTrue(User.create('foobar5', 'foobar5'))
        self.assertTrue(Message.create(User.find('foobar5'),'hello'))
        self.assertTrue(User.delete('foobar5'))

    def test_post_non_existing_user(self):
        self.assertTrue(User.create('foobar5', 'foobar5'))
        self.assertFalse(Message.create(User.find('foobar6'),'hello'))
        self.assertTrue(User.delete('foobar5'))


if __name__ == '__main__':
    unittest.main()