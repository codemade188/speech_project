# app/views/session.py

from flask import Blueprint, request, current_app
from datetime import datetime, timezone, timedelta
import jwt
from app.extensions     import db
from app.models         import Session
from app.utils.response import Result

session_bp = Blueprint('session', __name__, url_prefix='/api/session')

# 时区：北京时间 UTC+8
TZ8 = timezone(timedelta(hours=8))


def get_current_user_id():
    """从 Authorization: Bearer <token> 中解析 JWT，返回用户 ID 或 None"""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None
    token = auth.split(None, 1)[1]
    try:
        payload = jwt.decode(token,
                             current_app.config['SECRET_KEY'],
                             algorithms=['HS256'])
        return payload.get('sub')
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        return None


@session_bp.route('', methods=['POST'])
def create_session():
    """
    1. 创建新会话（需鉴权）
    请求头:
      Authorization: Bearer <token>
    请求体 JSON:
      { "session_name": "会话名称（可选，默认为“未命名”）" }
    """
    user_id = get_current_user_id()
    if not user_id:
        return Result.error(401, msg="Unauthorized")

    data = request.get_json() or {}
    session_name = data.get('session_name') or "未命名"

    now = datetime.now(TZ8)
    s = Session(
        user_id        = user_id,
        session_name   = session_name,
        created_at     = now,
        last_active_at = now
    )
    db.session.add(s)
    try:
        db.session.commit()
    except Exception:
        current_app.logger.exception("Failed to create session")
        db.session.rollback()
        return Result.error(500, msg="Failed to create session")

    return Result.created(
        data={
            "session_id":     s.session_id,
            "session_name":   s.session_name,
            "created_at":     s.created_at.isoformat(),
            "last_active_at": s.last_active_at.isoformat()
        },
        msg="Session created successfully"
    )


@session_bp.route('/user', methods=['GET'])
def list_user_sessions():
    """
    2. 获取当前用户所有会话（需鉴权）
    请求头:
      Authorization: Bearer <token>
    """
    user_id = get_current_user_id()
    if not user_id:
        return Result.error(401, msg="Unauthorized")

    sessions = (
        Session.query
        .filter_by(user_id=user_id)
        .order_by(Session.last_active_at.desc())
        .all()
    )
    data = [{
        "session_id":     s.session_id,
        "session_name":   s.session_name,
        "created_at":     s.created_at.isoformat(),
        "last_active_at": s.last_active_at.isoformat()
    } for s in sessions]
    return Result.ok(data=data)


@session_bp.route('/<string:session_id>', methods=['PUT'])
def rename_session(session_id):
    """
    3. 修改当前用户的某次会话名称（需鉴权）
    请求头:
      Authorization: Bearer <token>
    请求体 JSON:
      { "session_name": "新的名称" }
    """
    user_id = get_current_user_id()
    if not user_id:
        return Result.error(401, msg="Unauthorized")

    new_name = request.json.get('session_name')
    if not new_name:
        return Result.error(400, msg="Missing session_name")

    s = Session.query.get(session_id)
    if not s or s.user_id != user_id:
        return Result.error(404, msg="Session not found")

    s.session_name   = new_name
    s.last_active_at = datetime.now(TZ8)
    try:
        db.session.commit()
    except Exception:
        current_app.logger.exception("Failed to rename session")
        db.session.rollback()
        return Result.error(500, msg="Failed to rename session")

    return Result.ok(msg="Session renamed successfully")


@session_bp.route('/<string:session_id>/activate', methods=['PUT'])
def activate_session(session_id):
    """
    4. 激活（点击）当前用户的某次会话，更新 last_active_at（需鉴权）
    请求头:
      Authorization: Bearer <token>
    """
    user_id = get_current_user_id()
    if not user_id:
        return Result.error(401, msg="Unauthorized")

    s = Session.query.get(session_id)
    if not s or s.user_id != user_id:
        return Result.error(404, msg="Session not found")

    s.last_active_at = datetime.now(TZ8)
    try:
        db.session.commit()
    except Exception:
        current_app.logger.exception("Failed to activate session")
        db.session.rollback()
        return Result.error(500, msg="Failed to activate session")

    return Result.ok(msg="Session activated")
