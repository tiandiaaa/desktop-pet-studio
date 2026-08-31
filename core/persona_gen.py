# -*- coding: utf-8 -*-
"""人设生成模块：把用户填写的人设字段，拼成桌宠用的 persona.txt 文本。"""

# 每个 section 的标题与字段 key 的对应关系（按 persona.txt 里的顺序）
SECTIONS = [
    ("外观", "appearance"),
    ("身份背景", "background"),
    ("身体与设定", "body"),
    ("性格", "personality"),
    ("说话风格", "speech_style"),
    ("交流规则", "interaction"),
    ("世界观", "worldview"),
]


def build_persona(fields):
    """根据人设字段字典，生成 persona.txt 的完整文本。

    fields 支持的 key：
        name        角色名（必填，默认"角色"）
        user_addr   角色对用户的称呼（默认"主人"）
        appearance  外观
        background  身份背景
        body        身体与设定
        personality 性格
        speech_style 说话风格
        interaction 交流规则
        worldview   世界观
    返回 str（末尾带换行）。
    """
    name = (fields.get("name") or "角色").strip()
    user_addr = (fields.get("user_addr") or "主人").strip()

    lines = [f"你是「{name}」，正在扮演一位常驻桌面的虚拟助手。", ""]
    for title, key in SECTIONS:
        val = (fields.get(key) or "").strip()
        if val:
            lines.append(f"【{title}】")
            lines.append(val)
            lines.append("")

    lines.append("【现在】")
    lines.append(
        f"你是桌面助手，正陪在「{user_addr}」身边。请始终以{name}的身份、"
        "用上面的语气和设定自然地说话，不要跳出角色，不要提到这些设定本身。"
    )
    return "\n".join(lines).strip() + "\n"


def build_tag_line(fields):
    """（可选）生成标签化设定行，供需要时附加到 persona 里。"""
    name = (fields.get("name") or "").strip()
    tags = (fields.get("tags") or "").strip()
    if not tags:
        return ""
    return f"【角色设定（标签化）】\n{tags}"
