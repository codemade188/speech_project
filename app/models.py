# models.py - ORM 模型集中管理
# 导入时间类型、密码哈希工具、数据库实例和 ID 生成器

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db
from .utils.id_generator import gen_nanoid

class User(db.Model):
    """
    用户模型
    - 表名: users
    - 存储用户基本信息
    - 与 Session 和 PracticeRecord 建立一对多关系
    """
    __tablename__ = 'users'

    # 主键: 随机固定长度字符串 ID
    id             = db.Column(db.String(10), primary_key=True, default=gen_nanoid)
    # 用户名: 最大长度 64，唯一且不能为空
    username       = db.Column(db.String(64), unique=True, nullable=False)
    # 邮箱: 最大长度 120，唯一且不能为空
    email          = db.Column(db.String(120), unique=True, nullable=False)
    # 密码哈希: 哈希后的密码，使用 set_password / check_password 操作
    password_hash  = db.Column(db.String(256), nullable=False)
    # 个性签名: 最大长度 256，可为空
    signature      = db.Column(db.String(256), nullable=True)
    # 注册时间: 默认当前时间
    registered_at  = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # 关系: 一个用户可以有多个会话 (一对多)
    # back_populates='user' 表示 Session 模型中对应属性为 user
    # cascade='all, delete-orphan' 表示删除用户时，级联删除其所有会话
    sessions = db.relationship(
        'Session',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    # 关系: 一个用户可以有多条练习记录 (一对多)
    # back_populates='user' 对应 PracticeRecord 模型中的 user 属性
    practice_records = db.relationship(
        'PracticeRecord',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    def set_password(self, password: str):
        """对明文密码进行哈希并存储"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """验证明文密码与存储哈希是否匹配"""
        return check_password_hash(self.password_hash, password)

class Topic(db.Model):
    """
    题目主题模型
    - 表名: topics
    - 存储题目分类
    - 与 Question 建立一对多关系
    """
    __tablename__ = 'topics'

    topic_id = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(64), unique=True, nullable=False)

    # 关系: 一个主题下可有多道题目 (一对多)
    # back_populates='topic' 对应 Question.topic 属性
    questions = db.relationship(
        'Question',
        back_populates='topic',
        cascade='all, delete-orphan'
    )

class Question(db.Model):
    """
    题目模型
    - 表名: questions
    - 存储题目文本、主题外键、音频 URL
    - 与 Topic、PracticeRecord 建立关系
    """
    __tablename__ = 'questions'

    question_id = db.Column(db.String(10), primary_key=True, default=gen_nanoid)
    text        = db.Column(db.String(512), nullable=False)
    topic_id    = db.Column(
        db.Integer,
        db.ForeignKey('topics.topic_id', onupdate='CASCADE', ondelete='RESTRICT'),
        nullable=False
    )
    audio_url   = db.Column(db.String(2048), nullable=True)

    # 多对一: 每道题目属于一个主题
    # back_populates='questions' 对应 Topic.questions
    topic = db.relationship('Topic', back_populates='questions')

    # 一对多: 一道题可以出现在多条练习记录中
    # back_populates='question' 对应 PracticeRecord.question
    practice_records = db.relationship(
        'PracticeRecord',
        back_populates='question',
        cascade='all, delete-orphan'
    )

class Session(db.Model):
    __tablename__ = 'sessions'

    session_id     = db.Column(db.String(10), primary_key=True, default=gen_nanoid)
    user_id        = db.Column(db.String(10),
                               db.ForeignKey('users.id', onupdate='CASCADE', ondelete='CASCADE'),
                               nullable=False)
    session_name   = db.Column(db.String(128), nullable=False)

    # 创建时间
    created_at     = db.Column(db.DateTime, default=datetime.now, nullable=False)
    # 最近操作时间：每当用户对此会话有新动作，就更新它
    last_active_at = db.Column(db.DateTime,
                               default=datetime.now,
                               onupdate=datetime.now,
                               nullable=False)

    __table_args__ = (
        # 新增索引，支持按 user_id + last_active_at 快速排序
        db.Index('idx_sessions_user_last_active', 'user_id', 'last_active_at'),
    )

    user = db.relationship('User', back_populates='sessions')
    practice_records = db.relationship(
        'PracticeRecord',
        back_populates='session',
        cascade='all, delete-orphan'
    )



class PracticeRecord(db.Model):
    """
    练习记录模型
    - 表名: practice_records
    - 存储用户练习记录、练习时间、用户音频 key 以及各项评分
    - 与 User、Session、Question 建立关系
    """
    __tablename__ = 'practice_records'

    record_id        = db.Column(db.String(10), primary_key=True, default=gen_nanoid)
    user_id          = db.Column(
        db.String(10),
        db.ForeignKey('users.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False
    )
    session_id       = db.Column(
        db.String(10),
        db.ForeignKey('sessions.session_id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False
    )
    question_id      = db.Column(
        db.String(10),
        db.ForeignKey('questions.question_id', onupdate='CASCADE', ondelete='RESTRICT'),
        nullable=False
    )
    attempted_at     = db.Column(db.DateTime, default=datetime.now, nullable=False)
    user_audio_key   = db.Column(db.String(256), nullable=True)

    # —— 新增评分字段 ——
    accuracy_score   = db.Column(db.Float, nullable=False, default=0.0)
    fluency_score    = db.Column(db.Float, nullable=False, default=0.0)
    integrity_score  = db.Column(db.Float, nullable=False, default=0.0)
    standard_score   = db.Column(db.Float, nullable=False, default=0.0)
    total_score      = db.Column(db.Float, nullable=False, default=0.0)

    __table_args__ = (
        db.Index('idx_practice_user_time', 'user_id', 'attempted_at'),
        db.Index('idx_practice_session_time', 'session_id', 'attempted_at'),
    )

    # 多对一: 记录属于一个用户
    user     = db.relationship('User',    back_populates='practice_records')
    # 多对一: 记录属于一个会话
    session  = db.relationship('Session', back_populates='practice_records')
    # 多对一: 记录关联一道题目
    question = db.relationship('Question',back_populates='practice_records')