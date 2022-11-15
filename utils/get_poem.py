import random
import os

try:
    os.chdir(os.path.split(os.path.realpath(__file__))[0])
    with open('poem.txt', 'r', encoding='utf-8') as f:
        poem_list = f.read().splitlines()
except Exception:
    print("未找到诗词文件")
    poem_list = []


def get_poem() -> str:
    '''获取一句诗'''
    if len(poem_list) != 0:
        index = random.randint(0, len(poem_list) - 1)
        return poem_list[index]
    else:
        return ""
