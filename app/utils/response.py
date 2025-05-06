# app/utils/response.py

from flask import jsonify

class Result:
    """
    统一 API 返回结果封装，包含状态码、消息和数据三部分

    常用响应状态码及含义：
      200 -> 成功
      201 -> 资源已创建
      400 -> 请求参数错误
      401 -> 身份验证失败
      403 -> 没有访问权限
      404 -> 资源未找到
      500 -> 服务器内部错误
    """
    CODE_MESSAGES = {
        200: "成功",
        201: "资源已创建",
        400: "请求参数错误",
        401: "身份验证失败",
        403: "没有访问权限",
        404: "资源未找到",
        500: "服务器内部错误"
    }

    def __init__(self, code: int = 200, msg: str = None, data=None):
        self.code = code
        self.msg  = msg if msg is not None else self.CODE_MESSAGES.get(code, "")
        self.data = data

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "msg":  self.msg,
            "data": self.data
        }

    @staticmethod
    def ok(data=None, msg: str = None):
        """200 成功"""
        return jsonify(Result(200, msg, data).to_dict())

    @staticmethod
    def created(data=None, msg: str = None):
        """201 资源已创建"""
        return jsonify(Result(201, msg, data).to_dict())

    @staticmethod
    def error(code: int, msg: str = None, data=None):
        """4xx/5xx 统一错误返回"""
        return jsonify(Result(code, msg, data).to_dict())
