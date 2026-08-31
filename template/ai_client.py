import base64
import json

import requests


class AIClient:
    """可配置的 AI 客户端，支持 OpenAI 兼容接口（DeepSeek / OpenAI / Ollama 等）。"""

    def __init__(self, config_path="config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        ai = cfg["ai"]
        self.base_url = ai["base_url"].rstrip("/")
        self.api_key = ai.get("api_key", "")
        self.model = ai.get("model", "deepseek-chat")
        self.vision_model = ai.get("vision_model", self.model)
        self.temperature = ai.get("temperature", 0.9)
        self.max_history = ai.get("max_history", 20)
        self.keep_alive = ai.get("keep_alive", "30m")  # 模型常驻显存时长（Ollama）

    @property
    def is_ready(self):
        # 本地 Ollama 无需真实 API Key
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            return True
        key = self.api_key.strip()
        return bool(key) and "填写" not in key and key.lower() not in ("your_api_key",)

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(self, messages):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "keep_alive": self.keep_alive,
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def analyze_image(self, image_bytes, prompt):
        """把截图发给多模态模型，让它描述/评论屏幕内容。"""
        url = f"{self.base_url}/chat/completions"
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ]
        payload = {
            "model": self.vision_model,
            "messages": messages,
            "temperature": 0.7,
            "keep_alive": self.keep_alive,
        }
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
