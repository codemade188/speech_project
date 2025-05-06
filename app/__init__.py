# 创建 Flask app、加载配置、注册蓝图、初始化扩展

# app/__init__.py

from flask import Flask
from flask_cors import CORS
from .config import get_config
from .extensions import init_app_extensions
# 导入各个蓝图
from app.views.auth import auth_bp
from app.views.session import session_bp
from app.views.questions import questions_bp
from .views.evaluate import eval_bp
from app.views.statistics import stats_bp


def create_app():
    app = Flask(__name__, instance_relative_config=False)
    # 加载配置
    app.config.from_object(get_config())

    # 初始化 CORS，开放 /api 路由
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # 初始化各类扩展（db, migrate, cors, mail, celery, redis）
    init_app_extensions(app)

    # 注册认证模块蓝图，所有路由前缀自动加上 '/api/auth'
    app.register_blueprint(auth_bp)
    # 注册其他模块蓝图：
    app.register_blueprint(session_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(eval_bp)
    app.register_blueprint(stats_bp)

    return app
