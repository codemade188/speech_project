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
from pydub import AudioSegment

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


import os
import tempfile
import subprocess
import shlex
import wave
import xml.etree.ElementTree as ET

from flask import request, current_app
from werkzeug.utils import secure_filename

PROJECT_ROOT = r"D:\Pycharm_Projects\speech_project"
SILK_DECODER_EXE = os.path.join(PROJECT_ROOT, "tools", "silk-v3-decoder", "windows", "silk_v3_decoder.exe")


@eval_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """
    POST /api/evaluate/transcribe
    - 接收 form-data 的音频文件（.wav/.mp3/.m4a/.flac/.mp4/.silk）
    - 返回 JSON { code, msg, data: { text: 转写结果 } }
    """
    if 'file' not in request.files:
        return Result.error(400, msg="Missing audio file")
    file = request.files['file']
    if not file.filename:
        return Result.error(400, msg="Empty filename")

    filename = secure_filename(file.filename)
    suffix = os.path.splitext(filename)[1].lower()
    allowed_suffix = ('.wav', '.mp3', '.m4a', '.flac', '.mp4', '.silk')
    if suffix not in allowed_suffix:
        return Result.error(400, msg="Unsupported audio format")

    # 写入临时文件
    fd, src_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    tmp_wav_path = None
    try:
        file.save(src_path)

        if suffix == '.silk':
            # silk 解码为 pcm 文件
            pcm_path = src_path + '.pcm'
            cmd_decode = f'"{SILK_DECODER_EXE}" "{src_path}" "{pcm_path}"'
            subprocess.run(cmd_decode, shell=True, check=True)

            # pcm 转 wav，silk_v3_decoder输出默认24kHz单声道s16le
            fd_wav, tmp_wav_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd_wav)
            cmd_pcm2wav = f'ffmpeg -y -f s16le -ar 24000 -ac 1 -i "{pcm_path}" "{tmp_wav_path}"'
            subprocess.run(cmd_pcm2wav, shell=True, check=True)
            os.remove(pcm_path)
            os.remove(src_path)  # 原 silk 文件临时删除
            audio_path_for_transcribe = tmp_wav_path
        else:
            audio_path_for_transcribe = src_path

        # 调用 Whisper 转写
        try:
            model = get_whisper_model()
            result = model.transcribe(audio_path_for_transcribe, language=None, fp16=False)
            text = result.get('text', '').strip()
        except Exception as e:
            current_app.logger.exception("Whisper transcription failed")
            return Result.error(500, msg=f"Transcription error: {e}")

        return Result.ok(data={'text': text})

    finally:
        for p in (src_path, tmp_wav_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass


@eval_bp.route('/ise', methods=['POST'])
def ise_evaluate():
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

    # 3. 保存临时文件（支持任意格式）
    filename = secure_filename(f.filename)
    suffix = os.path.splitext(filename)[1].lower()
    allowed_exts = ('.wav', '.mp3', '.m4a', '.flac', '.mp4', '.aac', '.silk')
    if suffix not in allowed_exts:
        return Result.error(400, msg=f"Unsupported audio format: {suffix}")

    fd_src, src_path = tempfile.mkstemp(suffix=suffix)
    fd_dst, dst_path = tempfile.mkstemp(suffix='.wav')  # 输出始终为标准 wav
    os.close(fd_src)
    os.close(fd_dst)

    try:
        f.save(src_path)

        if suffix == '.silk':
            # 使用 silk_v3_decoder 解码成 PCM，再转成 16kHz WAV
            pcm_path = src_path + '.pcm'
            cmd_decode = f'"{SILK_DECODER_EXE}" "{src_path}" "{pcm_path}"'
            subprocess.run(cmd_decode, shell=True, check=True)

            cmd_pcm2wav = f'ffmpeg -y -f s16le -ar 16000 -ac 1 -i "{pcm_path}" "{dst_path}"'
            subprocess.run(cmd_pcm2wav, shell=True, check=True)

            os.remove(pcm_path)
            os.remove(src_path)
        else:
            # FFmpeg 转为 16kHz 单声道 PCM WAV
            cmd = f'ffmpeg -y -i "{src_path}" -ar 16000 -ac 1 "{dst_path}"'
            subprocess.run(shlex.split(cmd), check=True)

        # 4. 验证并读取音频数据
        with wave.open(dst_path, 'rb') as wf:
            if wf.getframerate() != 16000 or wf.getnchannels() != 1:
                return Result.error(500, msg="Transcoding failed to produce 16kHz mono WAV")

            duration = wf.getnframes() / wf.getframerate()
            if duration < 0.2:
                return Result.error(400, msg="音频过短或无效，可能未说话或格式转换失败")  # ✅ 新增判空逻辑

            audio_bytes = wf.readframes(wf.getnframes())

        # 5. 发给讯飞评测
        xml_b64_or_str = websocket_thread(audio_bytes, text)
        if not xml_b64_or_str:
            return Result.error(500, msg="Evaluation failed")

        # 6. 解析结果
        try:
            parsed = decode_and_parse(xml_b64_or_str)
        except Exception:
            root = ET.fromstring(xml_b64_or_str)
            parsed = etree_to_dict(root)

        if 'read_sentence' not in parsed:
            keys = list(parsed.keys())
            if len(keys) == 1:
                parsed = parsed[keys[0]]

        read_sentence = parsed.get('read_sentence', {})
        if isinstance(read_sentence, list):
            read_sentence = read_sentence[0]

        rec_paper = read_sentence.get('rec_paper', {})
        if isinstance(rec_paper, list):
            rec_paper = rec_paper[0]

        chapter = rec_paper.get('read_chapter', {})
        if isinstance(chapter, list):
            chapter = chapter[0]

        attrib = chapter.get('@attrib', {})

        summary = {
            'total_score':     float(attrib.get('total_score', 0)),
            'standard_score':  float(attrib.get('standard_score', 0)),
            'fluency_score':   float(attrib.get('fluency_score', 0)),
            'accuracy_score':  float(attrib.get('accuracy_score', 0)),
            'integrity_score': float(attrib.get('integrity_score', 0)),
        }

        words = []
        sentence = chapter.get('sentence', {})
        if isinstance(sentence, list):
            sentence = sentence[0]

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
            'words': words
        })

    except subprocess.CalledProcessError:
        current_app.logger.exception("FFmpeg or Silk decoding error")
        return Result.error(500, msg="Audio decoding or transcoding failed")
    except Exception as e:
        current_app.logger.exception("ISE evaluation error")
        return Result.error(500, msg=f"ISE error: {e}")
    finally:
        for p in (src_path, dst_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass








