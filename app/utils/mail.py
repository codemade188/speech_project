# app/utils/mail.py

from flask_mail import Message
from flask import current_app
from ..extensions import mail

def send_verification_code(to_email: str, code: str):
    """
    发送注册邮箱验证码
    """
    subject = "speech_project注册验证码"
    body    = f"您的注册验证码是：{code}，5 分钟内有效。"
    msg = Message(subject=subject,
                  recipients=[to_email],
                  body=body,
                  sender=current_app.config["MAIL_DEFAULT_SENDER"])
    mail.send(msg)
