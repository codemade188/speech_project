# app/utils/baidu_translate.py

import requests
import hashlib
import random
from flask import current_app

def translate_text(q: str,
                   from_lang: str = 'en',
                   to_lang:   str = 'zh') -> str:
    endpoint = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
    appid    = current_app.config['BAIDU_APPID']
    secret   = current_app.config['BAIDU_SECRET']
    salt     = str(random.randint(32768, 65536))
    sign     = hashlib.md5((appid + q + salt + secret).encode('utf-8')).hexdigest()

    params = {
        'q':     q,
        'from':  from_lang,
        'to':    to_lang,
        'appid': appid,
        'salt':  salt,
        'sign':  sign
    }

    resp = requests.get(
        endpoint,
        params=params,
        timeout=5,
        verify=False,                    # 若环境中 SSL 有校验问题可继续保留
        proxies={'http': None, 'https': None}  # 禁用代理，避免 check_hostname 错误
    )
    data = resp.json()

    if 'trans_result' in data and data['trans_result']:
        return data['trans_result'][0]['dst']
    else:
        err = data.get('error_msg') or data.get('error_code') or 'Unknown error'
        raise Exception(err)
