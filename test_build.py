# -*- coding: utf-8 -*-
"""端到端测试：人设 → 立绘 → 生成桌宠。"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.persona_gen import build_persona
from core.pet_builder import build_pet

# 1. 人设
fields = {
    "name": "测试助手",
    "user_addr": "前辈",
    "appearance": "银白色长发、蓝色眼睛，穿白色连衣裙。",
    "background": "一名热爱天文的天才少女，正在研究星空。",
    "personality": "温柔、好奇、有点迷糊。",
    "speech_style": "称呼对方为「前辈」，句尾常带「~」，语气软糯。",
    "interaction": "前辈沉默时会主动轻声搭话。",
    "worldview": "普通现代世界。",
}
persona = build_persona(fields)
print("=== persona.txt 内容 ===")
print(persona)

# 2. 立绘（复用艾雅法拉立绘作为测试输入）
src = r"C:\Users\86130\WorkBuddy\2026-08-20-18-25-51\艾雅法拉桌宠\assets\eyja_1.png"

# 3. 生成桌宠
pet_dir = build_pet(
    role_name="测试助手",
    persona_text=persona,
    portraits=[{"src": src, "width": 320}],
    ai_config={
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama",
        "model": "qwen2.5vl:7b",
        "vision_model": "qwen2.5vl:7b",
        "temperature": 0.9,
        "max_history": 20,
        "keep_alive": "30m",
    },
    pet_opts={"screenshot_interval_sec": 30},
)

print("\n=== 生成的桌宠目录结构 ===")
for root, dirs, files in os.walk(pet_dir):
    rel = os.path.relpath(root, pet_dir)
    for f in sorted(files):
        p = os.path.join(rel, f) if rel != "." else f
        print(" ", p)

print("\n=== config.json 内容 ===")
with open(os.path.join(pet_dir, "config.json"), encoding="utf-8") as f:
    print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
