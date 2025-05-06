"""
脚本：test_fetch_audio.py
功能：
 1. 读取环境变量中的华为云 OBS 配置。
 2. 指定一个测试题目的 question_id，并构造其 audio_url（standardVoice/{question_id}.wav）。
 3. 生成带签名的访问 URL（method='GET'，有效期 3600 秒）。
 4. 使用 OBS SDK 下载该音频到本地文件（downloadFile 参数）。
 5. 打印 HTTP 状态码及错误信息以便排查。

依赖：
  pip install obs-sdk python-dotenv

环境变量（.env 文件）：
  OBS_ACCESS_KEY
  OBS_SECRET_KEY
  OBS_ENDPOINT
  OBS_BUCKET

示例：
  python test_fetch_audio.py
"""
import os
import sys
from obs import ObsClient
from dotenv import load_dotenv

# ---------------- 环境准备 ----------------
load_dotenv()
OBS_ACCESS_KEY = os.getenv('OBS_ACCESS_KEY')
OBS_SECRET_KEY = os.getenv('OBS_SECRET_KEY')
OBS_ENDPOINT = os.getenv('OBS_ENDPOINT')
OBS_BUCKET = os.getenv('OBS_BUCKET')

# 校验环境变量
for name, val in [
    ('OBS_ACCESS_KEY', OBS_ACCESS_KEY),
    ('OBS_SECRET_KEY', OBS_SECRET_KEY),
    ('OBS_ENDPOINT', OBS_ENDPOINT),
    ('OBS_BUCKET', OBS_BUCKET),
]:
    if not val:
        print(f"请检查环境变量: {name}")
        sys.exit(1)

# 初始化 OBS 客户端
obs_client = ObsClient(
    access_key_id=OBS_ACCESS_KEY,
    secret_access_key=OBS_SECRET_KEY,
    server=OBS_ENDPOINT
)

# ---------------- 测试下载 ----------------
question_id = '03N1YH5OnB'  # 替换为你的测试 ID
object_key = f"standardVoice/{question_id}.wav"

# 生成签名 URL
signed = obs_client.createSignedUrl(
    bucketName=OBS_BUCKET,
    objectKey=object_key,
    expires=3600,
    method='GET'
)
print("签名访问 URL (1 小时内有效)：")
print(signed.get('signedUrl', signed))

# 使用签名 URL 通过 HTTP 下载到本地
from urllib import request as urlrequest

download_file = f"download_{question_id}.wav"
print(f"开始通过签名 URL 下载到本地: {download_file}")
signed_url_str = signed.get('signedUrl') or signed
try:
    urlrequest.urlretrieve(signed_url_str, download_file)
    print(f"下载成功，文件已保存在: {download_file}")
except Exception as e:
    print(f"下载失败，错误: {e}")
    sys.exit(1)
