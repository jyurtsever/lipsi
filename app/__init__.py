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


##Bundle js Assets
# js = Bundle('loading-bar.js')
#
# assets = Environment(app)
###
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'



from app import routes, models

app.redis = Redis.from_url(app.config['REDIS_URL'])
app.task_queue = rq.Queue('lipsi-tasks', connection=app.redis)

# def create_app(config_class=Config):
#     if app.config['LOG_TO_STDOUT']:
#         stream_handler = logging.StreamHandler()
#         stream_handler.setLevel(logging.INFO)
#         app.logger.addHandler(stream_handler)
#     else:
#         if not os.path.exists('logs'):
#             os.mkdir('logs')
#         file_handler = RotatingFileHandler('logs/lipsi.log',
#                                            maxBytes=10240, backupCount=10)
#         file_handler.setFormatter(logging.Formatter(
#             '%(asctime)s %(levelname)s: %(message)s '
#             '[in %(pathname)s:%(lineno)d]'))
#         file_handler.setLevel(logging.INFO)
#         app.logger.addHandler(file_handler)
#
#     print("oaidoiusofiu YOOOOOOOO")
#
#
#     app.logger.setLevel(logging.INFO)
#     app.logger.info('Lipsi startup')