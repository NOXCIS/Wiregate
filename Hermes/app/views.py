from app import app, db, lm
from flask import render_template, flash, redirect, session, url_for, request, g
from flask_login import login_user, logout_user, current_user, login_required
from .forms import LoginForm, MessageForm, PasswordForm, DeleteUser
from .models import User, Message


@app.route('/post', methods=['POST'])
@login_required
def post():
    form = MessageForm()

    # Handle the case when we send a message
    if form.validate_on_submit():
        # Adding the message to the database
        Message.create(g.user, form.message.data)
        # We redirect, we do not render the template. Otherwise
        # the form will be filled again.

    return redirect("/index")


@app.route('/')
@app.route('/home')
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = MessageForm()
    return render_template("index.html", title="Message Board", form=form)


@login_required
@app.route('/messages')
def get_messages():
    msgs = Message.query.order_by(Message.id.desc()).limit(20).all()[::-1]
    return render_template("messages.html", messages=msgs)


@lm.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.before_request
def before_request():
    g.user = current_user


@app.route('/admin/user/delete', methods=['POST'])
@login_required
def delete_user():
    if not g.user.is_admin:
        redirect("/")
    form = DeleteUser()
    if form.validate_on_submit():

        u = User.find(form.username.data)

        if u.username == g.user.username:
            flash("You cannot remove yourself")
            return redirect('/admin/user/list')
        if u:
            db.session.delete(u)
            db.session.commit()
    return redirect('/admin/user/list')


@app.route('/admin/user/add', methods=['GET', 'POST'])
@login_required
def adduser():
    if not g.user.is_admin:
        redirect("/")

    form = LoginForm()
    if form.validate_on_submit():
        # Check if users with this name exists
        if len(form.password.data) < 5:
            flash("Password should be at least 5 chars")
            return render_template('adduser.html',
                                   title='Add User',
                                   form=form)
        # Let's create the user
        if User.create(form.username.data, form.password.data):
            return redirect('/admin/user/list')

    return render_template('adduser.html',
                           title='Add User',
                           form=form)


@app.route('/admin/user/change-password', methods=['POST'])
@login_required
def change_password():
    if not g.user.is_admin:
        redirect("/")
    form = PasswordForm()
    u = User.query.filter(User.username == form.username.data)
    if u.count() != 1:
        flash("did not found user {}".format(form.username.data))
        return redirect("/admin/user/list")
    if len(form.password.data) < 5:
        flash("message length too small")
        return redirect("/admin/user/list")
    user_to_modify = u.first()
    user_to_modify.set_password(form.password.data)
    db.session.commit()
    return redirect("/admin/user/list")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user and g.user.is_authenticated:
        flash("You are already logged in")
        return redirect('/index')

    form = LoginForm()
    if form.validate_on_submit():

        users = User.query.filter(User.username == form.username.data)
        if users.count() != 1:
            flash('User %s does not exist' %
                  (form.username.data))
            return render_template('login.html',
                                   title='Sign In',
                                   form=form)
        user = users.first()
        if not user.check_password(form.password.data):
            flash('Invalid password for user %s' %
                  (form.username.data))
            return render_template('login.html',
                                   title='Sign In',
                                form=form)
        login_user(user)
        return redirect('/index')
    return render_template('login.html',
                           title='Sign In',
                           form=form)


@app.route('/admin/user/list', methods=['GET'])
@login_required
def list_users():
    # If the user is not admin, he comes
    # back to the front page
    if not g.user.is_admin:
        redirect('/')
    allusers=User.query.all()
    forms={}
    forms_delete={}
    for u in allusers:
        forms[u.username] = PasswordForm(username=u.username)
        forms_delete[u.username] = DeleteUser(username=u.username)
    return render_template('listusers.html',
                           title='List Users',
                           users=allusers,
                           forms=forms,
                           forms_delete=forms_delete)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = PasswordForm(username=g.user.username)
    if form.validate_on_submit():
        g.user.set_password(form.password.data)
        db.session.commit()
        return redirect('/index')
    return render_template('profile.html',
                           title='Profile',
                           form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found_error(error):
    flash("Page not found")
    return redirect("/")


@app.errorhandler(500)
def internal_error(error):
    flash("Internal error")
    return redirect("/")
