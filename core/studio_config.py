# -*- coding: utf-8 -*-
"""桌宠工坊的全局配置：GPT-SoVITS 路径、Python 路径、Ollama 地址等。

配置保存在 configs/studio.json，用户可在 GUI 的「环境设置」里修改。
"""

import json
import os

from core.paths import app_dir

CONFIG_PATH = os.path.join(app_dir(), "configs", "studio.json")

DEFAULTS = {
    # 发布到公开仓库时保持为空；使用者通过「环境设置」填写自己的路径。
    # pythonw 留空时，桌宠启动脚本会自动用当前 Python 同级的 pythonw.exe。
    "pythonw": "",
    "gptsovits_dir": "",
    "ollama_base_url": "http://localhost:11434",
}


def load_config():
    """读取配置，合并默认值。返回 dict。"""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update(data)
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    """保存配置到 configs/studio.json。"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get(key, default=None):
    return load_config().get(key, default)


def check_gptsovits(gptsovits_dir):
    """检测 GPT-SoVITS 整合包是否完整。返回 (ok, 缺失说明)。"""
    if not gptsovits_dir or not os.path.isdir(gptsovits_dir):
        return False, "目录不存在"
    api_py = os.path.join(gptsovits_dir, "api.py")
    runtime = os.path.join(gptsovits_dir, "runtime", "python.exe")
    if not os.path.isfile(api_py):
        return False, "缺少 api.py（不是 GPT-SoVITS 整合包根目录）"
    if not os.path.isfile(runtime):
        return False, "缺少 runtime/python.exe（整合包不完整）"
    return True, ""


def check_ollama(base_url):
    """检测 Ollama 服务是否在线。返回 bool。"""
    import socket
    from urllib.parse import urlparse
    try:
        parsed = urlparse(base_url or DEFAULTS["ollama_base_url"])
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        return True
    except Exception:
        return False
