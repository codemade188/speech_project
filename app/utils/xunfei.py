# 调用讯飞语音评测接口

import os
import urllib
from datetime import datetime
from dotenv import load_dotenv
import wave
import json
import base64
import time
import hmac
import hashlib
import threading
import xml.etree.ElementTree as ET  # 添加 XML 解析库
import websocket
from queue import Queue
from flask import Flask, jsonify, send_file, after_this_request, current_app,Response,request
import urllib.parse


# 加载环境变量
load_dotenv()

# 从环境变量中获取配置
API_KEY = os.getenv('XUNFEI_API_KEY')
API_SECRET = os.getenv('XUNFEI_API_SECRET')
APPID = os.getenv('XUNFEI_APPID')
HOST  = os.getenv('XUNFEI_HOST')
REQUEST_LINE = os.getenv("XUNFEI_REQUEST_LINE")


def get_rfc1123_time():
    return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

def assemble_url_and_headers():
    date       = get_rfc1123_time()
    sig_origin = f"host: {HOST}\ndate: {date}\n{REQUEST_LINE}"
    sig_sha    = hmac.new(API_SECRET.encode(), sig_origin.encode(), hashlib.sha256).digest()
    sig_base64 = base64.b64encode(sig_sha).decode()
    auth_origin = (
        f'api_key="{API_KEY}", algorithm="hmac-sha256", ' +
        f'headers="host date request-line", signature="{sig_base64}"'
    )
    auth_base64 = base64.b64encode(auth_origin.encode()).decode()
    params = urllib.parse.urlencode({
        "authorization": auth_base64,
        "date":          date,
        "host":          HOST
    })
    url = f"wss://{HOST}/v2/open-ise?{params}"
    headers = [
        f"Host: {HOST}",
        f"Date: {date}",
        f"Authorization: {auth_base64}"
    ]
    return url, headers





def on_open(ws, audio_bytes, text):
    """
    首帧：cmd=ssb，上送文本；随后分帧上传音频
    """
    def run():
        # ——— 首帧：参数阶段 ———
        first = {
            "common": {"app_id": APPID},
            "business": {
                "cmd":       "ssb",
                "sub":       "ise",
                "ent":       "en_vip",
                "category":  "read_sentence",
                "aue":       "raw",
                "auf":       "audio/L16;rate=16000",
                "text":      "\uFEFF" + text,
                "ttp_skip":  True
            },
            "data": {"status": 0}
        }
        ws.send(json.dumps(first))

        # ——— 音频上传阶段 ———
        chunk_size = 1280
        interval   = 0.04
        total      = len(audio_bytes)
        sent       = 0
        aus        = 1

        while sent < total:
            chunk = audio_bytes[sent: sent + chunk_size]
            sent += chunk_size

            frame = {
                "business": {"cmd": "auw", "aus": aus},
                "data":     {"status": 1, "data": base64.b64encode(chunk).decode()}
            }
            ws.send(json.dumps(frame))
            aus = 2  # 后续均为中间帧
            time.sleep(interval)

        # ——— 尾帧：status=2，结束上传 ———
        last = {
            "business": {"cmd": "auw", "aus": 4},
            "data":     {"status": 2}
        }
        ws.send(json.dumps(last))

    threading.Thread(target=run).start()


def websocket_thread(audio_bytes: bytes, text: str) -> str:
    """
    同步 WebSocket 调用，直接返回科大讯飞 data.data 字段（XML 原始字符串）。
    """
    url, headers = assemble_url_and_headers()
    result_queue = Queue()

    def on_message(ws, message):
        msg = json.loads(message)
        # 业务码不为 0
        if msg.get("code") != 0:
            result_queue.put(None)
            ws.close()
            return

        payload = msg.get("data", {})
        # status==2 表示最后一帧，此时 data 就是原始 XML
        if payload.get("status") == 2 and payload.get("data") is not None:
            xml_str = payload["data"]
            result_queue.put(xml_str)
            ws.close()

    def on_error(ws, error):
        result_queue.put(None)
        ws.close()

    ws_app = websocket.WebSocketApp(
        url,
        header     = headers,
        on_open    = lambda ws: on_open(ws, audio_bytes, text),
        on_message = on_message,
        on_error   = on_error,
        on_close   = lambda ws, code, msg: None
    )
    ws_app.run_forever()

    return result_queue.get()  # 取到的就是 XML 字符串，或 None（出错）




def etree_to_dict(elem):
    d = {}
    if elem.attrib:
        d['@attrib'] = dict(elem.attrib)
    children = list(elem)
    if children:
        dd = {}
        for child in children:
            child_res = etree_to_dict(child)
            tag = child.tag
            if tag in dd:
                if not isinstance(dd[tag], list):
                    dd[tag] = [dd[tag]]
                dd[tag].append(child_res[tag])
            else:
                dd[tag] = child_res[tag]
        d.update(dd)
    text = (elem.text or '').strip()
    if text:
        d['#text'] = text
    return {elem.tag: d}

# app/utils/xunfei.py

def decode_and_parse(xml_b64: str) -> dict:
    """
    接收 Base64 编码的 XML 字符串，解码、解析，并返回 dict 结果。
    抛出 Exception（或 ParseError）时由上层捕获。
    """
    import base64, xml.etree.ElementTree as ET
    xml_bytes = base64.b64decode(xml_b64)
    xml_str   = xml_bytes.decode('utf-8')
    root      = ET.fromstring(xml_str)
    return etree_to_dict(root)


