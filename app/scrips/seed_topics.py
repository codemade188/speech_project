#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
批量初始化 topics 表中的主题名称
"""

import os
from flask import Flask
from app.config     import get_config
from app.extensions import db
from app.models     import Topic

# 你爬取并准备要导入的主题列表
TOPIC_NAMES = [
    "Business",
    "Daily Life",
    "Interview",
    "Travel",
    # …如果还有更多主题就继续加进去
]

def seed_topics():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(get_config())
    db.init_app(app)

    with app.app_context():
        for name in TOPIC_NAMES:
            name = name.strip()
            if not Topic.query.filter_by(name=name).first():
                t = Topic(name=name)
                db.session.add(t)
                print(f"✔ 添加主题：{name}")
        db.session.commit()
        print("✅ topics 表初始化完成。")

if __name__ == "__main__":
    seed_topics()
