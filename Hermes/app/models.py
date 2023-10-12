from app import db
from sqlalchemy.sql import func
from passlib.hash import pbkdf2_sha256

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(120), index=False, unique=False)
    is_admin = db.Column(db.Boolean, unique=False, index=False)
    messages = db.relationship('Message', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User %r>' % (self.username)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @staticmethod
    def create(username, password):
        existing = User.query.filter(User.username == username)

        if existing.count() != 0:
            return False
        newuser = User(username=username,
                       password=password,
                       is_admin=False)
        newuser.set_password(password)
        db.session.add(newuser)
        db.session.commit()
        return True

    @staticmethod
    def find(username):
        found = User.query.filter(User.username == username)
        if found.count() == 1:
            return found.first()

    @staticmethod
    def delete(username):
        u = User.find(username)
        if u:
            db.session.delete(u)
            db.session.commit()
            return True
        return False

    def get_id(self):
        try:
            return unicode(self.id)  # python 2
        except NameError:
            return str(self.id)  # python 3

    def set_password(self, newpassword):
        h = pbkdf2_sha256.hash(newpassword)
        self.password = h

    def check_password(self, p):
        return pbkdf2_sha256.verify(p, self.password)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    content = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    @staticmethod
    def create(user, content):
        if not user:
            return False

        m = Message(content=content, author=user, timestamp=func.now())
        db.session.add(m)
        db.session.commit()
        return True

    def __repr__(self):
        return '<Message %r>' % (self.content)