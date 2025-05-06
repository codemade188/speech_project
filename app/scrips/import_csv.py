#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
app/import_csv.py

将 app/utils 目录下的 CSV 导入到 MySQL 的 questions 表
- CSV 仅包含两列：text, topic
- topic 名称映射到 topics 表中已存在的 topic_id（若不存在，则跳过此条）
- question_id 由 gen_nanoid 自动生成
- audio_url = question_id
- 忽略超过 512 字符的文本行
- 最多录入 250 条题目
"""

import os
import csv
import re
from flask import Flask

# 导入项目配置和扩展
from app.config import get_config
from app.extensions import db
from app.models import Topic, Question

# 文本清洗正则
SPACE_CLEAN  = re.compile(r'\s+')
MAX_TEXT_LEN = 512
MAX_TOTAL    = 250  # 最多导入的题目数量


def clean_text(text: str) -> str:
    """折叠多余空白，并去掉首尾空格。"""
    return SPACE_CLEAN.sub(' ', text).strip()


def import_questions(csv_path: str):
    """主函数：从 CSV 读取并入库，使用已存在 topics 映射，跳过过长文本"""
    topic_map = {t.name: t.topic_id for t in Topic.query.all()}
    print(f"已加载主题映射: {topic_map}")

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for row in reader:
            if count >= MAX_TOTAL:
                print(f"⚠️ 已达到题目上限 {MAX_TOTAL}，提前结束导入")
                break

            raw_text = clean_text(row['text'])
            if len(raw_text) > MAX_TEXT_LEN:
                print(f"⚠️ 跳过过长文本 ({len(raw_text)} chars): {raw_text[:50]}...")
                continue

            topic_name = row['topic'].strip()
            if topic_name not in topic_map:
                print(f"⚠️ 跳过未知主题: {topic_name}")
                continue

            topic_id = topic_map[topic_name]
            q = Question(text=raw_text, topic_id=topic_id)
            db.session.add(q)
            db.session.flush()
            q.audio_url = q.question_id
            count += 1

        db.session.commit()
        print(f"✅ 导入完成，共写入 {count} 条记录。")


if __name__ == '__main__':
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(get_config())
    db.init_app(app)

    base_dir = os.path.dirname(__file__)
    utils_dir = os.path.join(base_dir, 'utils')
    csv_file = os.path.join(utils_dir, 'questions_Travel.csv')

    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"找不到 CSV 文件：{csv_file}")

    with app.app_context():
        import_questions(csv_file)
