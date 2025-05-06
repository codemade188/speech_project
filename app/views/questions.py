# app/views/questions.py

import re
from flask import Blueprint, request, current_app
from obs import ObsClient
from sqlalchemy import func
from app.models         import Question
from app.extensions     import db
from app.utils.baidu_translate import translate_text
from app.utils.presigned import get_reference_audio_url
from app.utils.response import Result


questions_bp = Blueprint('questions', __name__, url_prefix='/api/questions')


# app/views/questions.py

import re
from flask import Blueprint, request, current_app
from sqlalchemy import func
from app.models         import Question, Topic
from app.extensions     import db
from app.utils.response import Result

questions_bp = Blueprint('questions', __name__, url_prefix='/api/questions')


@questions_bp.route('', methods=['GET'])
def get_questions():
    """
    根据主题、关键词和数量随机返回题目（最大数量 100）

    查询参数（均可为空）:
      - topic_id: 主题 ID（整数）
      - keywords: 关键词，空格或逗号分隔
      - limit:    返回题目数量，默认 10，最大 100

    返回:
      {
        "code": 200,
        "msg": "成功",
        "data": {
          "count": 5,
          "questions": [ ... ]
        }
      }
    """
    topic_id = request.args.get('topic_id', type=int)
    keywords = request.args.get('keywords', '', type=str).strip()
    limit    = request.args.get('limit',    type=int, default=10)

    if limit is None or limit <= 0:
        return Result.error(400, msg="limit 必须为正整数")
    if limit > 100:
        limit = 100

    query = Question.query
    if topic_id is not None:
        query = query.filter(Question.topic_id == topic_id)

    if keywords:
        terms = [kw for kw in re.split(r'[\s,]+', keywords) if kw]
        for term in terms:
            query = query.filter(Question.text.ilike(f"%{term}%"))

    try:
        questions = (query
                     .order_by(func.rand())
                     .limit(limit)
                     .all())
    except Exception:
        current_app.logger.exception("查询题目失败")
        return Result.error(500, msg="获取题目失败")

    questions_list = []
    for q in questions:
        topic_name = q.topic.name if q.topic else None
        questions_list.append({
            'question_id': q.question_id,
            'text':        q.text,
            'audio_url':   q.audio_url,
            'topic_id':    q.topic_id,
            'topic_name':  topic_name
        })

    response_data = {
        'count':     len(questions_list),
        'questions': questions_list
    }
    return Result.ok(data=response_data)


@questions_bp.route('/topics', methods=['GET'])
def get_topics():
    """
    获取所有题目主题及每个主题下的题目总数

    返回:
      {
        "code": 200,
        "msg": "成功",
        "data": [
          { "topic_id": 1, "name": "Business",    "question_count": 42 },
          { "topic_id": 2, "name": "Daily Life",  "question_count": 37 },
          ...
        ]
      }
    """

    try:
        # LEFT JOIN Questions, 按 topic 聚合计数
        rows = (
            db.session.query(
                Topic.topic_id,
                Topic.name,
                func.count(Question.question_id).label('question_count')
            )
            .outerjoin(Question, Question.topic_id == Topic.topic_id)
            .group_by(Topic.topic_id)
            .order_by(Topic.name)
            .all()
        )
    except Exception:
        current_app.logger.exception("查询主题失败")
        return Result.error(500, msg="获取主题失败")

    data = [
        {
            'topic_id':      tid,
            'name':          name,
            'question_count': count
        }
        for tid, name, count in rows
    ]
    return Result.ok(data=data)


@questions_bp.route('/<string:question_id>/audio-url', methods=['GET'])
def get_reference_url(question_id):
    """
    生成某题参考音频的临时签名 URL
    """
    q = Question.query.get(question_id)
    if not q or not q.audio_url:
        return Result.error(404, msg="找不到题目或参考音频")

    try:
        url = get_reference_audio_url(question_id)
    except Exception as e:
        current_app.logger.exception("生成参考音频签名 URL 失败: %s", e)
        return Result.error(500, msg=f"生成签名 URL 失败: {e}")

    return Result.ok(data={'url': url})


@questions_bp.route('/<string:question_id>/translate', methods=['GET'])
def translate_question(question_id):
    """
    根据 question_id 获取题干并翻译成中文
    """
    q = Question.query.get(question_id)
    if not q:
        return Result.error(404, msg='Question not found')

    try:
        # 原文
        src_text = q.text
        # 调用翻译工具
        dst_text = translate_text(src_text, from_lang='en', to_lang='zh')
    except Exception as e:
        current_app.logger.exception("翻译失败: %s", e)
        return Result.error(500, msg=f"Translation failed: {e}")

    # 返回原文与译文
    return Result.ok(data={
      'original': src_text,
      'translated': dst_text
    })


