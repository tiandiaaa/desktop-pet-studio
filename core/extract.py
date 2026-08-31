# -*- coding: utf-8 -*-
"""从一大段角色文字中用 AI 提取人设字段（名称、外观、性格、背景等）。"""

import json
import re

import requests

PROMPT_TEMPLATE = """从下面这段角色描述中，提取以下字段，只输出一个 JSON 对象，不要任何其他内容（不要 markdown 代码块、不要解释、不要注释）：
字段名（均为字符串，原文没提到的就留空字符串）：
- name: 角色名
- user_addr: 角色对用户的称呼（如「主人」「前辈」，没提到就空）
- appearance: 外观（长相、发型、服装）
- background: 身份背景（出身、职业、经历）
- body: 身体与设定（疾病、特殊能力、宠物等）
- personality: 性格
- speech_style: 说话风格（语气、口头禅、称呼方式）
- interaction: 交流规则（如沉默时主动搭话、特定场景反应）
- worldview: 世界观（所处世界的设定）

角色描述：
{text}
"""


def parse_json(content):
    """从 AI 输出中解析 JSON（容忍 ```json 包裹、前后废话）。返回 dict。"""
    content = (content or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.S)
    if m:
        content = m.group(1)
    else:
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end > start:
            content = content[start:end + 1]
    try:
        data = json.loads(content)
        if not isinstance(data, dict):
            return {}
        out = {}
        for k, v in data.items():
            if isinstance(v, (str, int, float)):
                out[k] = str(v)
            elif isinstance(v, list):
                out[k] = "、".join(str(x) for x in v)
        return out
    except Exception:
        return {}


def extract_fields(text, base_url, api_key, model, temperature=0.2, timeout=120):
    """调用 OpenAI 兼容接口，从文字中提取人设字段。

    base_url  接口地址（如 http://localhost:11434/v1 或 https://api.deepseek.com/v1）
    api_key   API Key（Ollama 可填 "ollama"）
    model     模型名
    返回 dict（失败返回空 dict）。
    """
    if not text.strip():
        return {}
    prompt = PROMPT_TEMPLATE.format(text=text)
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return parse_json(content)
    except Exception:
        return {}
