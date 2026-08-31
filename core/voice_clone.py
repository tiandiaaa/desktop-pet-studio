# -*- coding: utf-8 -*-
"""零样本声音克隆模块：用户提交参考音频 → 生成 voice 配置（无需训练）。

零样本克隆原理：GPT-SoVITS 用预训练模型 + 一段参考音频，即可合成该音色，
不需要像艾雅法拉那样训练专属模型。门槛低、几分钟就能用。
"""

import os
import shutil
import wave

from core.paths import resource_dir


def probe_audio(path):
    """读取 wav 音频的时长/采样率。返回 dict 或 None（非 wav 或读取失败）。"""
    try:
        with wave.open(path, "rb") as w:
            dur = w.getnframes() / w.getframerate()
            return {
                "duration": round(dur, 2),
                "framerate": w.getframerate(),
                "channels": w.getnchannels(),
            }
    except Exception:
        return None


def prepare_voice(ref_audio_path, ref_text, ref_lang, role_dir, speed=0.85):
    """把参考音频复制进桌宠目录，返回 voice 配置 dict。

    ref_audio_path  用户提交的参考音频（wav，3~10 秒效果最佳）
    ref_text        参考音频里说的内容（可为空，有则更准）
    ref_lang        参考音频语种：中文 / 日文 / 英文
    role_dir        桌宠输出目录
    """
    os.makedirs(os.path.join(role_dir, "voice"), exist_ok=True)
    ext = os.path.splitext(ref_audio_path)[1].lower() or ".wav"
    dst = os.path.join(role_dir, "voice", f"ref{ext}")
    shutil.copyfile(ref_audio_path, dst)

    info = probe_audio(dst)
    return {
        "ref_wav": dst,
        "ref_text": (ref_text or "").strip(),
        "ref_lang": ref_lang or "中文",
        "speed": speed,
        "duration": info.get("duration", 0) if info else 0,
        "note": "" if not info else _duration_note(info.get("duration", 0)),
    }


def _duration_note(duration):
    if duration < 3:
        return "参考音频偏短（<3 秒），建议 3~10 秒效果更稳"
    if duration > 10:
        return "参考音频偏长（>10 秒），建议 3~10 秒"
    return "时长合适"


def deploy_start_tts(gptsovits_dir):
    """把通用 start_tts_user.py 部署到 GPT-SoVITS 目录，返回目标路径。"""
    src = os.path.join(resource_dir(), "gptsovits_assets", "start_tts_user.py")
    dst = os.path.join(gptsovits_dir, "start_tts_user.py")
    shutil.copyfile(src, dst)
    return dst
