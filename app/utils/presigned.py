# app/utils/presigned.py

from flask import current_app
from app.utils.obs_client import client as obs_client  # 已初始化的 ObsClient 实例


def generate_presigned_url(object_key: str,
                           method: str = 'GET',
                           expires: int = 3600) -> str:
    """
    通用签名 URL 生成器，仅返回签名 URL 字符串
    """
    # 调用 OBS SDK 生成签名，resp 里包含 signedUrl 和 headers
    resp = obs_client.createSignedUrl(
        method     = method,
        bucketName = current_app.config['OBS_BUCKET'],
        objectKey  = object_key,
        expires    = expires
    )

    # SDK v1 返回 dict-like 或对象，取其 signedUrl 属性／键
    if hasattr(resp, 'signedUrl'):
        return resp.signedUrl
    if isinstance(resp, dict) and 'signedUrl' in resp:
        return resp['signedUrl']

    # 回退：直接返回 resp 自身字符串化结果
    return str(resp)


def get_reference_audio_url(question_id: str, expires: int = 3600) -> str:
    """
    获得某题参考音频的下载签名 URL
    OBS 存储路径：standardVoice/{question_id}.wav
    """
    key = f"standardVoice/{question_id}.wav"
    return generate_presigned_url(key, method='GET', expires=expires)


def get_user_audio_url(record_id: str, expires: int = 3600) -> str:
    """
    获得用户音频的下载签名 URL
    OBS 存储路径：userVoice/{record_id}.wav
    """
    key = f"userVoice/{record_id}.wav"
    return generate_presigned_url(key, method='GET', expires=expires)
