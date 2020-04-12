web: flask db upgrade; flask translate compile; gunicorn lipsi:app
worker: rq worker -u $REDIS_URL microblog-tasks
