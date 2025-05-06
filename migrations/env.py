import sys, os
# 在 this file 目录上一级添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import logging
from logging.config import fileConfig

from flask import current_app
from alembic import context

# 导入 SQLAlchemy 实例和所有 ORM 模型，确保 Metadata 注册
from app.extensions import db
from app.models     import User, Topic, Question, Session, PracticeRecord

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # Flask-SQLAlchemy <3
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # Flask-SQLAlchemy >=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace('%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')

# 设置 sqlalchemy.url
config.set_main_option('sqlalchemy.url', get_engine_url())

# 获取 target_db
target_db = current_app.extensions['migrate'].db


def get_metadata():
    # Flask-SQLAlchemy>=3 使用 metadatas，<3 使用 metadata
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


# run_migrations_offline and run_migrations_online 保持不变，使用 get_metadata() 代替 None

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get('process_revision_directives') is None:
        conf_args['process_revision_directives'] = process_revision_directives

    connectable = get_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
