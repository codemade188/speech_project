# app/api/auth.py

from flask import Blueprint, request, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app.models         import User
from app.utils.mail     import send_verification_code
from app.utils.response import Result
import app.extensions as ext
import jwt  # pip install PyJWT
from datetime import datetime, timezone, timedelta
import random
import string
import json  # 用于序列化/反序列化临时数据

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    第一步：接收 username, email, password
    - 检查表中是否已有该用户名/邮箱
    - 生成验证码，发送邮件
    - 将待激活用户数据（username/password_hash）+ code 序列化后存 Redis，60s 后过期
    """
    data = request.get_json() or {}
    username = data.get('username')
    email    = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return Result.error(400, 'Username, email and password are required')

    # 表中已存在时直接拒绝
    if User.query.filter((User.email == email) | (User.username == username)).first():
        return Result.error(409, 'Username or email already in use')

    # 生成 6 位数字验证码
    code = ''.join(random.choices(string.digits, k=6))

    # 准备存 Redis 的临时数据
    temp = {
        'username':      username,
        'password_hash': generate_password_hash(password),
        'code':          code,
        'created_at':    datetime.now(timezone(timedelta(hours=8))).isoformat()
    }

    try:
        # 发送验证码邮件
        send_verification_code(to_email=email, code=code)
        # 存储到 Redis，key = register_data:<email>
        ext.redis_client.setex(
            f"register_data:{email}",
            60,
            json.dumps(temp)
        )
    except Exception as e:
        current_app.logger.exception("Failed to send verification email or write Redis")
        return Result.error(500, 'Registration failed, please try again')

    return Result.created(
        msg='Verification code sent to email; please verify within 60 seconds'
    )


@auth_bp.route('/verify', methods=['POST'])
def verify():
    """
    第二步：校验验证码并真正创建用户
    请求体：
      {
        "email": "xxx@example.com",
        "code":  "123456"
      }
    """
    data  = request.get_json() or {}
    email = data.get('email')
    code  = data.get('code')

    if not email or not code:
        return Result.error(400, 'Email and code are required')

    # 1. 从 Redis 取回临时注册数据
    raw = ext.redis_client.get(f"register_data:{email}")
    if not raw:
        return Result.error(400, 'No pending registration or code expired')

    temp = json.loads(raw)
    # 2. 验证 code
    if code != temp.get('code'):
        return Result.error(400, 'Invalid verification code')

    # 3. 创建用户
    try:
        user = User(
            username=temp['username'],
            email=email,
            registered_at=datetime.now(timezone(timedelta(hours=8)))
        )
        user.password_hash = temp['password_hash']
        ext.db.session.add(user)
        ext.db.session.commit()
    except Exception as e:
        current_app.logger.exception("Failed to create user after verification")
        ext.db.session.rollback()
        return Result.error(500, 'Activation failed, please try again')

    # 4. 删除 Redis 临时数据
    ext.redis_client.delete(f"register_data:{email}")

    # 5. 返回新用户信息
    user_data = {
        'id':            user.id,
        'username':      user.username,
        'email':         user.email,
        'registered_at': user.registered_at.isoformat()
    }
    return Result.created(
        data={'user': user_data},
        msg='User activated and created successfully'
    )


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    第三步：登录接口，仅需 username + password，成功则签发 JWT
    """
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return Result.error(400, 'Username and password required')

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return Result.error(401, 'Invalid credentials')

    # 签发 JWT (8 小时过期，北京时间 iat/exp)
    tz8 = timezone(timedelta(hours=8))
    now = datetime.now(tz8)
    payload = {
        'sub': user.id,
        'iat': now,
        'exp': now + timedelta(hours=8)
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    user_data = {
        'id':            user.id,
        'username':      user.username,
        'email':         user.email,
        'registered_at': user.registered_at.isoformat()
    }
    return Result.ok(data={'token': token, 'user': user_data})


@auth_bp.route('/userinfo', methods=['GET'])
def userinfo():
    """
    获取当前登录用户信息:
      从 Authorization: Bearer <token> 解析 JWT
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Result.error(401, 'Missing or invalid token')

    token = auth_header.split(None, 1)[1]
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return Result.error(401, 'Token expired')
    except jwt.InvalidTokenError:
        return Result.error(401, 'Invalid token')

    user = User.query.get(payload['sub'])
    if not user:
        return Result.error(404, 'User not found')

    user_data = {
        'id':            user.id,
        'username':      user.username,
        'email':         user.email,
        'registered_at': user.registered_at.isoformat()
    }
    return Result.ok(data={'user': user_data})
