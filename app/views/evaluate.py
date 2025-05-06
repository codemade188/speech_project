# 讯飞评分接口和 XML → JSON 解析
#Whisper对用户语音进行文本转写
#音素对比

# app/views/evaluate.py

# app/views/evaluate.py

# app/views/evaluate.py

import os
import tempfile
import wave
import subprocess
import shlex
import whisper
from flask import Blueprint, request, current_app
from werkzeug.utils import secure_filename 
import xml.etree.ElementTree as ET  # 添加 XML 解析库
from app.models import Question
from app.utils.response import Result
from app.utils.xunfei import etree_to_dict,websocket_thread,decode_and_parse

import warnings
warnings.filterwarnings("ignore", message=".*weights_only=False.*", category=FutureWarning)


eval_bp = Blueprint('evaluate', __name__, url_prefix='/api/evaluate')

# 全局模型实例
_model = None

def get_whisper_model():
    """
    懒加载 Whisper 模型，并指定本地缓存目录：
      - cache_dir: D:\whisper_cache
      - download_root: Whisper 会把模型权重存放在此处
    """
    global _model
    if _model is None:
        # 1. 确保缓存目录存在
        cache_dir = r"D:\whisper_cache"
        os.makedirs(cache_dir, exist_ok=True)

        # 2. 加载模型并指定 download_root
        model_name = current_app.config.get('WHISPER_MODEL', 'tiny')
        _model = whisper.load_model(
            model_name,
            download_root=cache_dir
        )
    return _model


@eval_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """
    POST /api/evaluate/transcribe
    - 接收 form-data 的音频文件（.wav/.mp3/.m4a/.flac/.mp4）
    - 返回 JSON { code, msg, data: { text: 转写结果 } }
    """
    # 验证上传
    if 'file' not in request.files:
        return Result.error(400, msg="Missing audio file")
    file = request.files['file']
    if not file.filename:
        return Result.error(400, msg="Empty filename")

    # 校验格式
    filename = secure_filename(file.filename)
    suffix   = os.path.splitext(filename)[1].lower()
    if suffix not in ('.wav', '.mp3', '.m4a', '.flac', '.mp4'):
        return Result.error(400, msg="Unsupported audio format")

    # 写入临时文件（兼容 Windows）
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    try:
        file.save(tmp_path)

        # 调用 Whisper 转写
        try:
            model  = get_whisper_model()
            result = model.transcribe(tmp_path, language=None, fp16=False)
            text   = result.get('text', '').strip()
        except Exception as e:
            current_app.logger.exception("Whisper transcription failed")
            return Result.error(500, msg=f"Transcription error: {e}")

        return Result.ok(data={'text': text})

    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@eval_bp.route('/ise', methods=['POST'])
def ise_evaluate():
    """
    POST /api/evaluate/ise
    form-data:
      - question_id: 题目 ID（string）
      - audio:       任意采样率／声道的 WAV 文件

    后端流程：
      1. 保存上传文件
      2. 调用 FFmpeg 转码至 16kHz 单声道 WAV
      3. 读取 PCM 数据并发给讯飞 WebSocket
      4. Base64 解码并解析 XML → dict
      5. 扁平化提取分数返回
    """
    # 1. 入参校验
    qid = request.form.get('question_id')
    if not qid:
        return Result.error(400, msg="Missing question_id")
    if 'audio' not in request.files:
        return Result.error(400, msg="Missing audio file")
    f = request.files['audio']
    if not f.filename:
        return Result.error(400, msg="Empty filename")

    # 2. 查询题干
    question = Question.query.get(qid)
    if not question:
        return Result.error(404, msg="Question not found")
    text = question.text

    # 3. 保存并转码
    filename = secure_filename(f.filename)
    if not filename.lower().endswith('.wav'):
        return Result.error(400, msg="Please upload a .wav file")

    fd_src, src_path = tempfile.mkstemp(suffix='.wav')
    fd_dst, dst_path = tempfile.mkstemp(suffix='.wav')
    os.close(fd_src); os.close(fd_dst)

    try:
        # 保存上传的原始文件
        f.save(src_path)

        # FFmpeg 转码到 16kHz 单声道
        cmd = (
            f'ffmpeg -y '
            f'-i "{src_path}" '
            f'-ar 16000 '
            f'-ac 1 '
            f'"{dst_path}"'
        )
        subprocess.run(shlex.split(cmd), check=True)

        # 4. 用 wave 验证并读取 PCM
        with wave.open(dst_path, 'rb') as wf:
            if wf.getframerate() != 16000 or wf.getnchannels() != 1:
                return Result.error(500, msg="Transcoding failed to produce 16kHz mono")
            audio_bytes = wf.readframes(wf.getnframes())

        # 5. 调用讯飞 WebSocket 评测
        xml_b64_or_str = websocket_thread(audio_bytes, text)
        if not xml_b64_or_str:
            return Result.error(500, msg="Evaluation failed")

        # 6. Base64 解码并解析 XML → dict
        try:
            parsed = decode_and_parse(xml_b64_or_str)
        except Exception:
            root = ET.fromstring(xml_b64_or_str)
            parsed = etree_to_dict(root)

        # —— 新增：自动拆掉最外层包装 ——
        if 'read_sentence' not in parsed:
            keys = list(parsed.keys())
            if len(keys) == 1:
                parsed = parsed[keys[0]]

        # 7. 扁平化提取 summary & words
        chapter = (
            parsed
            .get('read_sentence', {})
            .get('rec_paper', {})
            .get('read_chapter', {})
        )
        attrib = chapter.get('@attrib', {})

        # summary 部分说明：
        #   total_score     ：整句朗读的总分（满分 5.0）
        #   standard_score  ：与标准发音的对比得分
        #   fluency_score   ：流畅度得分
        #   accuracy_score  ：发音准确度得分
        #   integrity_score ：朗读完整度得分
        summary = {
            'total_score':     float(attrib.get('total_score', 0)),
            'standard_score':  float(attrib.get('standard_score', 0)),
            'fluency_score':   float(attrib.get('fluency_score', 0)),
            'accuracy_score':  float(attrib.get('accuracy_score', 0)),
            'integrity_score': float(attrib.get('integrity_score', 0)),
        }

        # words 部分说明：
        #   每个元素代表一句话中某个单词的评测结果，包括：
        #     text         ：词文本
        #     score        ：此词总分
        #     accuracy     ：发音准确度
        #     fluency      ：流畅度
        #     global_index ：在句子内的词序索引
        words = []
        sentence = chapter.get('sentence', {})
        word_list = sentence.get('word', [])
        if isinstance(word_list, dict):
            word_list = [word_list]
        for w in word_list:
            w_at = w.get('@attrib', {})
            words.append({
                'text':         w_at.get('content', ''),
                'score':        float(w_at.get('total_score', 0)),
                'accuracy':     float(w_at.get('accuracy_score', 0)),
                'fluency':      float(w_at.get('fluency_score', 0)),
                'global_index': int(w_at.get('global_index', 0))
            })

        return Result.ok(data={
            'summary': summary,
            'words':   words
        })

    except subprocess.CalledProcessError:
        current_app.logger.exception("FFmpeg transcoding error")
        return Result.error(500, msg="Audio transcoding failed")
    except Exception as e:
        current_app.logger.exception("ISE evaluation error")
        return Result.error(500, msg=f"ISE error: {e}")
    finally:
        for path in (src_path, dst_path):
            try:
                os.remove(path)
            except OSError:
                pass







