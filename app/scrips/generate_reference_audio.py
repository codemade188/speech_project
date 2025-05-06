"""
脚本：generate_reference_audio.py
功能：
 1. 从 MySQL 数据库的 questions 表中读取所有题目文本及其 question_id（假设主键列名为 question_id）。
 2. 使用 pyttsx3 本地合成每个题目的语音文件（WAV），命名为 "{question_id}.wav"。
    - 设置语速和音量：将语速(rate)调低，整体音量(volume)调高。
 3. 将语音文件上传到华为云 OBS 桶的 standardVoice/ 目录。
 4. 更新数据库中对应记录的 audio_url 字段为上传后的对象键 (standardVoice/{question_id}.wav)。
 5. 出错时打印调试信息，包含出错的 question_id 及当前已成功生成音频的数量；随后退出脚本。

依赖：
  pip install pyttsx3 obs-sdk pymysql python-dotenv

环境变量（.env 文件）：
  # OBS 配置
  OBS_ACCESS_KEY      # 华为云 OBS Access Key
  OBS_SECRET_KEY      # 华为云 OBS Secret Key
  OBS_ENDPOINT        # 华为云 OBS Endpoint，仅填域名或带 https:// 前缀
  OBS_BUCKET          # OBS 桶名称

  # MySQL 数据库配置
  DB_HOST             # 数据库主机
  DB_PORT             # 数据库端口
  DB_USER             # 数据库用户名
  DB_PASS             # 数据库密码
  DB_NAME             # 数据库名称

示例 .env：
  OBS_ACCESS_KEY=HPUAR0FUYPSEVUAP9NGW
  OBS_SECRET_KEY=7iofP7xt2MykOo7a4X7z28R9yEcK8FFmSEhTh0J5
  OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com
  OBS_BUCKET=my-audio-bucket

  DB_HOST=localhost
  DB_PORT=3306
  DB_USER=root
  DB_PASS=123456
  DB_NAME=speech_project
"""
import os
import sys
import ssl
import tempfile
import logging
import traceback
import pyttsx3
import pymysql
from obs import ObsClient
from dotenv import load_dotenv

# ---------------- 环境准备 ----------------
# 禁用系统代理，避免 SSL 握手失败
for var in ('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy'):
    os.environ.pop(var, None)
# 全局取消 SSL 验证，如需严格校验可移除此行
ssl._create_default_https_context = ssl._create_unverified_context

# 加载环境变量
load_dotenv()
# OBS 配置
OBS_ACCESS_KEY = os.getenv('OBS_ACCESS_KEY')
OBS_SECRET_KEY = os.getenv('OBS_SECRET_KEY')
OBS_ENDPOINT = os.getenv('OBS_ENDPOINT') or ''
if not OBS_ENDPOINT.startswith(('http://','https://')):
    OBS_ENDPOINT = 'https://' + OBS_ENDPOINT.strip('/')
OBS_BUCKET = os.getenv('OBS_BUCKET')
# MySQL 配置
DB_HOST = os.getenv('DB_HOST')
DB_PORT = int(os.getenv('DB_PORT',3306))
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_NAME = os.getenv('DB_NAME')

# 校验必要环境变量
for name, val in [
    ('OBS_ACCESS_KEY',OBS_ACCESS_KEY),
    ('OBS_SECRET_KEY',OBS_SECRET_KEY),
    ('OBS_ENDPOINT',OBS_ENDPOINT),
    ('OBS_BUCKET',OBS_BUCKET),
    ('DB_HOST',DB_HOST),
    ('DB_USER',DB_USER),
    ('DB_PASS',DB_PASS),
    ('DB_NAME',DB_NAME)
]:
    if not val:
        raise RuntimeError(f"环境变量 {name} 未配置，请检查 .env 文件。")

# 日志配置
logging.basicConfig(format='[%(levelname)s] %(asctime)s - %(message)s', level=logging.INFO)

# 初始化 OBS 客户端
obs_client = ObsClient(
    access_key_id=OBS_ACCESS_KEY,
    secret_access_key=OBS_SECRET_KEY,
    server=OBS_ENDPOINT
)

# ---------------- 主逻辑 ----------------
def main():
    # 1. 连接数据库
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    success_count = 0

    try:
        # 2. 获取所有题目
        cursor.execute("SELECT question_id, text FROM questions")
        rows = cursor.fetchall()
        total = len(rows)
        logging.info(f"共查询到 {total} 条题目记录。")

        # 3. 遍历合成并上传
        for question_id, text in rows:
            logging.info(f"[{success_count}/{total}] 开始处理 question_id={question_id}")
            local_path = None
            try:
                # 3.1 初始化 TTS 引擎并调整语速与音量
                engine = pyttsx3.init()
                engine.setProperty('rate', 150)    # 默认为200，可根据需求调低
                engine.setProperty('volume', 1.0)  # 范围0.0–1.0，最大音量

                # 合成到本地 WAV 文件
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    local_path = tmp.name
                engine.save_to_file(text, local_path)
                engine.runAndWait()
                engine.stop()
                logging.debug(f"本地临时文件: {local_path}")

                # 3.2 上传至 OBS
                object_key = f"standardVoice/{question_id}.wav"
                resp = obs_client.putFile(
                    OBS_BUCKET,
                    object_key,
                    file_path=local_path
                )
                if resp.status < 300:
                    # 3.3 更新数据库
                    cursor.execute(
                        "UPDATE questions SET audio_url=%s WHERE question_id=%s",
                        (object_key, question_id)
                    )
                    conn.commit()
                    success_count += 1
                    logging.info(f"成功生成音频: question_id={question_id}")
                else:
                    raise RuntimeError(f"OBS 上传失败: status={resp.status}, message={resp.errorMessage}")

            except Exception as e:
                # 出错时报告并退出
                logging.error(f"处理出错 question_id={question_id}, 已成功 {success_count} 条, 错误: {e}")
                logging.debug(traceback.format_exc())
                sys.exit(1)

            finally:
                # 删除临时文件
                if local_path and os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except Exception:
                        logging.warning(f"删除临时文件失败: {local_path}")

    finally:
        cursor.close()
        conn.close()
        logging.info(f"脚本结束, 成功生成 {success_count}/{total} 条音频。")

if __name__ == '__main__':
    main()
