# 配置类：MySQL、Redis、OBS、讯飞、Celery 等

# app/config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BaseConfig:
    # —— 基础 Flask 配置 ——
    SECRET_KEY = os.getenv("SECRET_KEY", "change_this_in_prod")  # 用于会话签名，生产环境务必覆盖

    # —— 数据库 ——
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASS}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # —— 缓存 & 异步任务 ——
    REDIS_URL             = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL     = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)
    CELERY_TASK_SERIALIZER = os.getenv("CELERY_TASK_SERIALIZER", "json")
    CELERY_RESULT_EXPIRES  = int(os.getenv("CELERY_RESULT_EXPIRES", "60"))      # 结果保留秒数
    CELERY_TIMEZONE        = os.getenv("CELERY_TIMEZONE", "Asia/Shanghai")     # 北京时间
    CELERY_ENABLE_UTC      = False                                            # 关闭 UTC 强制模式

    # —— 华为云 OBS ——
    OBS_ACCESS_KEY = os.getenv("OBS_ACCESS_KEY")
    OBS_SECRET_KEY = os.getenv("OBS_SECRET_KEY")
    OBS_ENDPOINT   = os.getenv("OBS_ENDPOINT")
    OBS_BUCKET     = os.getenv("OBS_BUCKET")

    # —— 科大讯飞评测 ——
    XUNFEI_API_KEY     = os.getenv("XUNFEI_API_KEY")
    XUNFEI_API_SECRET  = os.getenv("XUNFEI_API_SECRET")
    XUNFEI_APPID       = os.getenv("XUNFEI_APPID")
    XUNFEI_HOST        = os.getenv("XUNFEI_HOST")
    XUNFEI_REQUEST_LINE = os.getenv("XUNFEI_REQUEST_LINE")

    # —— 邮件服务配置 ——
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USE_TLS = False
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    # —— JWT配置 ——
    SECRET_KEY = os.getenv("SECRET_KEY", "change_this_in_prod")

    # —— 百度翻译api配置 ——
    BAIDU_APPID = os.getenv("BAIDU_APPID")
    BAIDU_SECRET = os.getenv("BAIDU_SECRET")

    # —— 外部题库 (Quiz API) ——
    QUIZAPI_URL = os.getenv("QUIZAPI_URL")
    QUIZAPI_KEY = os.getenv("QUIZAPI_KEY")

class DevelopmentConfig(BaseConfig):
    DEBUG = True

class TestingConfig(BaseConfig):
    TESTING = True

class ProductionConfig(BaseConfig):
    DEBUG = False

# Mapping for easy retrieval
config_map = {
    "development": DevelopmentConfig,
    "test": TestingConfig,
    "production": ProductionConfig,
}

def get_config():
    env = os.getenv("APP_ENV", "development").lower()
    return config_map.get(env, DevelopmentConfig)
