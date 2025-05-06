import os
from obs import ObsClient
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 从环境变量中获取配置
access_key = os.getenv('OBS_ACCESS_KEY')
secret_key = os.getenv('OBS_SECRET_KEY')
endpoint = os.getenv('OBS_ENDPOINT')
bucket_name = os.getenv('OBS_BUCKET')

# 初始化 ObsClient
client = ObsClient(
    access_key_id=access_key,
    secret_access_key=secret_key,
    server=endpoint
)


