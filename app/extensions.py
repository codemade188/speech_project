# 初始化扩展：db, celery, cors, migrate 等

# app/extensions.py

from flask_sqlalchemy import SQLAlchemy
from flask_migrate    import Migrate
from flask_cors       import CORS
from flask_mail       import Mail
from celery           import Celery
from redis            import Redis

db      = SQLAlchemy()
migrate = Migrate()
cors    = CORS()
mail    = Mail()
celery  = Celery(__name__, include=["celery_app.tasks"])
redis_client = None   # 先定义


def init_app_extensions(app):
    # —— SQLAlchemy ——
    db.init_app(app)

    # —— Alembic / Flask-Migrate ——
    migrate.init_app(app, db)

    # —— CORS ——
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Accept", "Authorization"],
        methods=["GET", "POST", "OPTIONS"]
    )

    # —— Flask-Mail ——
    mail.init_app(app)

    # —— Celery ——
    celery.conf.update(
        broker_url      = app.config["CELERY_BROKER_URL"],
        result_backend  = app.config["CELERY_RESULT_BACKEND"],
        task_serializer = app.config["CELERY_TASK_SERIALIZER"],
        result_expires  = app.config["CELERY_RESULT_EXPIRES"],
        timezone        = app.config["CELERY_TIMEZONE"],
        enable_utc      = app.config["CELERY_ENABLE_UTC"],
    )

    # —— Redis 客户端 ——
    global redis_client
    redis_client = Redis.from_url(
        app.config["REDIS_URL"],
        decode_responses=True    # 返回 str 而不是 bytes
    )

    return celery

