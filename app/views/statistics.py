#返回练习记录统计结果

# app/views/statistics.py
import json
from flask import Blueprint, request, current_app
from ..models import PracticeRecord,Question,Topic
from ..extensions import db
from ..utils.presigned import get_user_audio_url
from ..utils.response import Result
from ..utils.obs_client import client   # 已初始化的 ObsClient 实例
from sqlalchemy import func
from datetime import datetime, timedelta


stats_bp = Blueprint('statistics', __name__, url_prefix='/api/statistics')


@stats_bp.route('/practice_records', methods=['POST'])
def create_practice_record():
    """
    创建一条练习记录并上传用户音频到华为云 OBS（无需鉴权）。
    前端需以 multipart/form-data 提交：
      - user_id     (str)
      - session_id  (str)
      - question_id (str)
      - summary     (str: JSON.dump 五项评分)
      - audio       (file: wav)
    """
    user_id     = request.form.get('user_id')
    session_id  = request.form.get('session_id')
    question_id = request.form.get('question_id')
    summary_str = request.form.get('summary')
    audio_file  = request.files.get('audio')

    if not all([user_id, session_id, question_id, summary_str, audio_file]):
        return Result.error(400, '缺少必要参数或音频文件'), 400

    try:
        summary = json.loads(summary_str)
        acc   = float(summary.get('accuracy_score',   0.0))
        flu   = float(summary.get('fluency_score',     0.0))
        integ = float(summary.get('integrity_score',   0.0))
        std   = float(summary.get('standard_score',    0.0))
        tot   = float(summary.get('total_score',       0.0))
    except (ValueError, TypeError):
        return Result.error(400, 'summary 字段格式错误，应为合法 JSON'), 400

    record = PracticeRecord(
        user_id        = user_id,
        session_id     = session_id,
        question_id    = question_id,
        accuracy_score = acc,
        fluency_score  = flu,
        integrity_score= integ,
        standard_score = std,
        total_score    = tot
    )
    db.session.add(record)
    db.session.flush()

    bucket     = current_app.config['OBS_BUCKET']
    object_key = f"userVoice/{record.record_id}.wav"
    try:
        client.putObject(bucket, object_key, audio_file.stream)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"OBS 上传失败：{e}")
        return Result.error(500, '音频上传失败，请稍后重试'), 500

    record.user_audio_key = object_key
    db.session.commit()

    return Result.created({
        "record_id":      record.record_id,
        "user_audio_key": object_key
    }), 201



@stats_bp.route('/sessions/<session_id>/practice_records', methods=['GET'])
def get_records_by_session(session_id):
    """
    根据 session_id 获取该会话下所有练习记录，按练习时间升序返回
    """
    records = (
        PracticeRecord.query
        .filter_by(session_id=session_id)
        .order_by(PracticeRecord.attempted_at.asc())
        .all()
    )
    data = []
    for rec in records:
        data.append({
            "record_id":      rec.record_id,
            "question_id":    rec.question_id,
            "attempted_at":   rec.attempted_at.isoformat(),
            "summary": {
                "accuracy_score":   rec.accuracy_score,
                "fluency_score":    rec.fluency_score,
                "integrity_score":  rec.integrity_score,
                "standard_score":   rec.standard_score,
                "total_score":      rec.total_score,
            },
            "audio_url": get_user_audio_url(rec.record_id)
        })

    return Result.ok(data)


@stats_bp.route('/practice_counts', methods=['GET'])
def get_user_practice_counts():
    """
    获取当前用户过去一周、半个月和一个月每天的练习次数。
    前端需传入：
      - user_id (query param)
    返回：
      {
        'weekly': [ { date: 'YYYY-MM-DD', count: int }, ... ],
        'half_month': [ ... ],
        'monthly': [ ... ]
      }
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return Result.error(400, '缺少 user_id 参数'), 400

    today = datetime.now().date()

    def accumulate(days: int):
        start_date = today - timedelta(days=days-1)
        # 按日期统计
        rows = (
            db.session.query(
                func.date(PracticeRecord.attempted_at).label('day'),
                func.count(PracticeRecord.record_id).label('count')
            )
            .filter(
                PracticeRecord.user_id == user_id,
                PracticeRecord.attempted_at >= start_date
            )
            .group_by('day')
            .all()
        )
        counts = {row.day.isoformat(): row.count for row in rows}
        result = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            result.append({ 'date': d.isoformat(), 'count': counts.get(d.isoformat(), 0) })
        return result

    weekly     = accumulate(7)
    half_month = accumulate(15)
    monthly    = accumulate(30)

    return Result.ok({ 'weekly': weekly, 'half_month': half_month, 'monthly': monthly })



@stats_bp.route('/topic_distribution', methods=['GET'])
def get_topic_distribution():
    """
    获取指定用户在给定时间范围内，各话题练习题目数量分布。
    前端需传入查询参数：
      - user_id    (str)
      - start_date (YYYY-MM-DD)
      - end_date   (YYYY-MM-DD)
    返回：
      { distribution: [ { topic: str, count: int }, ... ] }
    """
    user_id    = request.args.get('user_id')
    start_date = request.args.get('start_date')
    end_date   = request.args.get('end_date')
    if not all([user_id, start_date, end_date]):
        return Result.error(400, '缺少 user_id、start_date 或 end_date 参数'), 400

    # 解析日期
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end   = datetime.strptime(end_date,   '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        return Result.error(400, '日期格式错误，需为 YYYY-MM-DD'), 400

    # 按话题统计
    rows = (
        db.session.query(
            Topic.name.label('topic'),
            func.count(PracticeRecord.record_id).label('count')
        )
        .join(Question, PracticeRecord.question_id == Question.question_id)
        .join(Topic, Question.topic_id == Topic.topic_id)
        .filter(
            PracticeRecord.user_id == user_id,
            PracticeRecord.attempted_at >= start,
            PracticeRecord.attempted_at <  end
        )
        .group_by(Topic.name)
        .all()
    )

    distribution = [ { 'topic': row.topic, 'count': row.count } for row in rows ]
    return Result.ok({ 'distribution': distribution })
