import json
from app import app, db
from app.forms import LoginForm, RegistrationForm, WikiSeedLinkForm
from flask import render_template, flash, redirect, url_for, make_response, jsonify
from flask_login import current_user, login_user, login_required, logout_user
from flask import request
from werkzeug.urls import url_parse
from app.models import User
from app.graph import *

options_dict = {"use_il": 0, "use_graph": 1}
opt = options_dict['use_graph']

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

    if opt == 0:
        return render_template('display_infinite_scroll.html', url= {'data': seed_link})
    elif opt == 1:
        force_g_dict = json.dumps(graph_from_seed(seed_link))
        print("rendering html")
        return render_template('display_graph.html', force_g_data=force_g_dict)
    else:
        links = wiki_make_lst_from_seed(seed_link)
        return render_template('display_url_lst.html', links=links[:50])#redirect(link)

@app.route('/load') #, methods=['GET'])
def load():
    limit = 30
    seed_link = request.args.get('url')
    links = wiki_make_lst_from_seed(seed_link)
    print("hello")
    if opt == 0:
        counter = int(request.args.get("c"))  # The 'counter' value sent in the QS

        if counter == 0:
            print(f"Returning posts 0 to {limit}")
            # Slice 0 -> quantity from the db
            res = make_response(jsonify(links[0: limit]), 200)

        elif counter == len(links):
            print("No more posts")
            res = make_response(jsonify({}), 200)

        else:
            print(f"Returning posts {counter} to {counter + limit}")
            # Slice counter -> quantity from the db
            res = make_response(jsonify(links[counter: counter + limit]), 200)
        return res
