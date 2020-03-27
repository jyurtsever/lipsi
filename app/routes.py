from app import app, db
from app.forms import LoginForm, RegistrationForm, WikiSeedLinkForm
from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_user, login_required, logout_user
from flask import request
from werkzeug.urls import url_parse
from app.models import User
from app.graph import *

@app.route('/')
@app.route('/index')
@login_required
def index():
    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'username': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        }
    ]
    return render_template('index.html', title='Home', posts=posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title="Sign In", form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/prompt_seed', methods=['GET', 'POST'])
@login_required
def prompt_seed():
    """
    Todo:
    prompt user to enter link of their choice
    :return:
    """
    form = WikiSeedLinkForm()
    if form.validate_on_submit():
        return redirect(url_for('seed', url=form.seed.data))
    return render_template('seed.html', title='Seed Link', form=form)


@app.route('/seed', methods=['GET'])
def seed():
    """
    Todo:
    start graph display of most interesting content
    related to link
    """
    seed_link = request.args.get('url')
    links = make_lst_from_seed(seed_link)
    return render_template('display_url_lst.html', links=links[:50])#redirect(link)
