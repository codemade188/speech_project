# run.py

from flask import Flask
from flask_cors import CORS      # ← 新增
from app import create_app

app = create_app()

# 允许任意来源访问所有路由
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/')
def hello_world():
    return '这是flask开发的英语口语学习项目speech_project'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
