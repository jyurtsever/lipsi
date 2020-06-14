import logging
import os
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from logging.handlers import SMTPHandler, RotatingFileHandler
from redis import Redis
from flask_assets import Bundle, Environment

import rq

app = Flask(__name__)


app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'



from app import routes, models

app.redis = Redis.from_url(app.config['REDIS_URL'])
app.task_queue = rq.Queue('lipsi-tasks', connection=app.redis)
