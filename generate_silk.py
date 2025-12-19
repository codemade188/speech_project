import os
import subprocess
import pyttsx3
from pydub import AudioSegment

# 根路径
PROJECT_ROOT = "D:/Pycharm_Projects/speech_project"

# encoder 路径
ENCODER_PATH = os.path.join(PROJECT_ROOT, "tools/silk-v3-decoder/windows/silk_v3_encoder.exe")


def text_to_wav(text, wav_path):
    # 初始化 pyttsx3 引擎
    engine = pyttsx3.init()

    # 可选：调整说话速度和音量
    engine.setProperty('rate', 150)  # 语速
    engine.setProperty('volume', 1.0)  # 音量（范围0.0~1.0）

    print(f"[🔊] Generating WAV from text using pyttsx3...")

    # 保存语音为 wav 文件
    engine.save_to_file(text, wav_path)
    engine.runAndWait()

    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"WAV 文件未成功生成：{wav_path}")
    if os.path.getsize(wav_path) < 1000:
        raise ValueError(f"WAV 文件太小，语音合成可能失败：{wav_path}")

    print(f"[✓] Exported WAV to: {wav_path}")


def wav_to_silk(wav_path, silk_path):
    if not os.path.exists(ENCODER_PATH):
        raise FileNotFoundError(f"编码器未找到：{ENCODER_PATH}")
    cmd = f'"{ENCODER_PATH}" "{wav_path}" "{silk_path}" -rate 16000'
    subprocess.run(cmd, shell=True, check=True)


def generate_silk_from_text(text, silk_path):
    wav_path = "temp_output.wav"
    text_to_wav(text, wav_path)
    wav_to_silk(wav_path, silk_path)
    os.remove(wav_path)
    print(f"[✅] .silk 文件生成成功：{silk_path}")


# 示例调用
if __name__ == "__main__":
    example_text = "Can you point me towards the gate?"
    output_path = os.path.join(PROJECT_ROOT, "test_output.silk")
    generate_silk_from_text(example_text, output_path)
