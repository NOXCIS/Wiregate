# """Test the sockets package."""
#
# from app import app, socket_io
# from app.models import db, Channel, User
# from app.sockets import add_message, announce_message
# from app.bcrypt.utils import hash_password
#
# def login(client, email, password):
#     return client.post('/', data=dict(
#         email=email,
#         password=password
#     ), follow_redirects=True)
#
#
# def logout(client):
#     return client.get('/logout', follow_redirects=True)
#
# def test_add_message():
#     app.config['TESTING'] = True
#     app.config['WTF_CSRF_ENABLED'] = False
#
#     with app.app_context():
#         db.drop_all()
#         db.create_all()
#
#         user = User(username='test_username', password=hash_password('test_password'), email='test@email.com')
#         db.session.add(user)
#
#         test_client = app.test_client()
#         rv = login(test_client, 'test@email.com', 'test_password')
#         assert rv.status_code == 200
#         assert 'Log out' in str(rv.data)  # Log out text must appear on the website after login.
#
#         channel = Channel(name='channelName', password='password')
#         db.session.add(channel)
#         socket_client = socket_io.test_client(app=app, flask_test_client=test_client)
#         socket_io.emit('join room', {'room': channel.name})
#         socket_io.emit('add message', {'channel': 'channelName', 'message_content': 'content'})
#         received = socket_client.get_received()
#         print(received)