import json
import urllib.parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, WikiSeedLinkForm
from flask import render_template, flash, redirect, url_for, make_response, jsonify, current_app, Response
from flask_login import current_user, login_user, login_required, logout_user
from flask import request
from werkzeug.urls import url_parse
from app.models import User
from app.graph import *
from app.wiki_objects import WikiPage

options_dict = {"use_il": 0, "use_graph": 1}
opt = options_dict['use_graph']

@app.route('/')
@app.route('/index')
# @login_required
def index():
    return redirect(url_for('prompt_seed'))

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
# @login_required
def prompt_seed():
    """
    Todo:
    prompt user to enter link of their choice
    :return:
    """
    form = WikiSeedLinkForm()
    if form.validate_on_submit():
        return redirect(url_for('load_graph', url=urllib.parse.quote(form.seed.data)))
    return render_template('seed.html', title='Seed Link', form=form)

@app.route('/autocomplete',methods=['GET'])
def autocomplete():
    semi_title = request.args.get('term')
    titles = WikiPage.prefix_search(semi_title)
    return Response(json.dumps(titles), mimetype='application/json')

@app.route('/load_graph', methods=['Get'])
def load_graph():
    """
    Starts job for generating graph
    :return: Loading screen for generating graph
    """
    url = urllib.parse.unquote(request.args.get('url'))
    queue = current_app.task_queue
    job = queue.enqueue('app.graph.graph_from_seed', url)
    job.meta['progress'] = 0
    job.save_meta()
    return render_template('load_graph.html', url=urllib.parse.quote(url), job_id=job.id)


@app.route('/job_status')
def job_status():
    """
    :return: JSon of job status and progress given url
    """
    job_id = request.args.get('job_id')
    queue = current_app.task_queue
    job = queue.fetch_job(job_id)
    if job is None:
        response = {'status': 'unknown'}
    else:
        job.refresh()
        progress = 0
        if 'progress' in job.meta:
            progress = job.meta['progress']
        response = {
            'status': job.get_status(),
            'progress': progress
            # 'result': job.result,
        }
        if job.is_failed:
            response['message'] = job.exc_info.strip().split('\n')[-1]
    return jsonify(response)

@app.route('/make_graph', methods=['GET'])
def make_graph():
    """
    Todo:
    start graph display of most interesting content
    related to link
    """
    seed_link = urllib.parse.unquote(request.args.get('url'))
    print("seed link: ", seed_link)
    if opt == 0:
        return render_template('display_infinite_scroll.html', url= {'data': seed_link})
    elif opt == 1:

        job_id = request.args.get('job_id')
        print("job_id", job_id)
        queue = current_app.task_queue
        job = queue.fetch_job(job_id)
        if not job:
            return redirect(url_for('load_graph', url=seed_link))
        force_g_dict = job.result
        print("rendering html")
        return render_template('display_graph.html', force_g_data=force_g_dict)
    else:
        links = wiki_make_lst_from_seed(seed_link)
        return render_template('display_url_lst.html', links=links[:50])

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
