import json
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "chat_memory.json")
KEEP_DAYS = 7
KEEP_SECONDS = KEEP_DAYS * 24 * 3600


def load_memory():
    """加载最近 7 天的聊天记忆。返回 (history, chat_log)，均为带 ts 字段的列表。"""
    if not os.path.exists(MEMORY_FILE):
        return [], []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return [], []
    cutoff = time.time() - KEEP_SECONDS
    history = [m for m in data.get("history", []) if m.get("ts", 0) >= cutoff]
    chat_log = [m for m in data.get("chat_log", []) if m.get("ts", 0) >= cutoff]
    return history, chat_log


def save_memory(history, chat_log):
    """保存聊天记忆。history 应不含 system 消息。"""
    data = {
        "history": history,
        "chat_log": chat_log,
    }
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
