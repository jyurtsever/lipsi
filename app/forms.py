from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, URL
from app.models import User
from app.wiki_objects import WikiPage
import httplib2
import urllib.parse

def check_url_exists(url_string):
    h = httplib2.Http()
    resp = h.request(url_string, 'HEAD')
    return int(resp[0]['status']) < 400

def validate_wikipedia_article_name(form, field):
    if not check_url_exists('https://en.wikipedia.org/wiki/' + urllib.parse.quote(field.data)):
        titles = WikiPage.prefix_search(field.data)
        if titles:
            raise ValidationError(f"Invalid Wikipedia article '{field.data}', did you mean '{titles[0]}'?")
        else:
            raise ValidationError(f"Invalid Wikipedia article '{field.data}'")


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class WikiSeedLinkForm(FlaskForm):
    """
    Form for seed link to start the graph
    """
    seed = StringField('Wikipedia Seed Link', id='seed', validators=[DataRequired(), validate_wikipedia_article_name])
    submit = SubmitField('Run!')


