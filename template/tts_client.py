"""桌宠的语音合成（TTS）客户端：调用本地 GPT-SoVITS 服务 + 中文→日语翻译。

参考音频、文本等语音参数从 config.json 的 voice 字段读取，本文件为通用模板，
不同角色的桌宠只需在 config.json 里配置各自的 voice 即可。
"""
import json
import os
import socket
from urllib.parse import urlparse

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TTS_BASE_URL = "http://127.0.0.1:9880"


class TTSClient:
    def __init__(self, config_path=None):
        self.base_url = TTS_BASE_URL
        self.enabled = True
        self.ref_wav = ""
        self.ref_text = ""
        self.ref_lang = "中文"
        self.speed = 0.85
        if config_path:
            self._load_config(config_path)

    def _load_config(self, config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, ValueError):
            return
        voice = cfg.get("voice", {})
        self.enabled = voice.get("enabled", True)
        self.base_url = voice.get("base_url", TTS_BASE_URL)
        self.ref_wav = voice.get("ref_wav", "")
        self.ref_text = voice.get("ref_text", "")
        self.ref_lang = voice.get("ref_lang", "中文")
        self.speed = voice.get("speed", 0.85)

    def is_ready(self):
        """检查 TTS 服务是否在线（用 TCP 连通性测试）。"""
        if not self.enabled:
            return False
        try:
            parsed = urlparse(self.base_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 9880
            s = socket.create_connection((host, port), timeout=2)
            s.close()
            return True
        except Exception:
            return False

    def synthesize(self, text, lang="中文", speed=None):
        """合成语音，返回 wav 字节；失败返回 None。"""
        if not self.ref_wav:
            return None
        sp = speed if speed is not None else self.speed
        data = {
            "refer_wav_path": self.ref_wav,
            "prompt_text": self.ref_text,
            "prompt_language": self.ref_lang,
            "text": text,
            "text_language": lang,
            "speed": sp,
        }
        try:
            r = requests.post(f"{self.base_url}/", json=data, timeout=120)
            if r.status_code == 200 and len(r.content) > 1000:
                return r.content
        except Exception:
            pass
        return None


def translate_zh_to_ja(text, ai_client):
    """用桌宠的 AI（Ollama/API）把中文翻译成日语。失败返回原文本。"""
    if not ai_client or not ai_client.is_ready:
        return text
    try:
        resp = ai_client.chat([
            {
                "role": "user",
                "content": (
                    "请把下面这句中文翻译成自然的日语，只输出日语译文本身，"
                    "不要加引号、解释或任何其他内容：\n" + text
                ),
            }
        ])
        resp = resp.strip().strip('"').strip("「」")
        return resp if resp else text
    except Exception:
        return text
