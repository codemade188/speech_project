# app/utils/id_generator.py

from nanoid import generate

# 自定义字母表（数字+大小写字母），长度 10
ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
ID_SIZE  = 10

def gen_nanoid() -> str:
    """
    生成一个长度为 ID_SIZE 的 nanoid，用于主键。
    碰撞概率极低，且长度固定，适合用作文件路径中的 ID。
    """
    return generate(ALPHABET, ID_SIZE)


