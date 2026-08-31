# -*- coding: utf-8 -*-
"""把桌宠工坊打包成一个干净的可分发文件夹（纯复制，不影响原艾雅法拉桌宠）。"""

import os
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(os.path.dirname(BASE), "桌宠工坊_发布版")

FILES = ["studio.py", "README.md", "requirements.txt", "安装说明.md"]
DIRS = ["core", "template", "gptsovits_assets"]


def copy_tree(src, dst):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(root, src)
        for f in files:
            if f.endswith(".pyc"):
                continue
            s = os.path.join(root, f)
            d = os.path.join(dst, rel, f) if rel != "." else os.path.join(dst, f)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copyfile(s, d)


def main():
    os.makedirs(DIST, exist_ok=True)
    os.makedirs(os.path.join(DIST, "output"), exist_ok=True)
    os.makedirs(os.path.join(DIST, "configs"), exist_ok=True)

    for f in FILES:
        src = os.path.join(BASE, f)
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(DIST, f))
    for d in DIRS:
        copy_tree(os.path.join(BASE, d), os.path.join(DIST, d))

    # 启动脚本：双击启动向导 GUI
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    launcher = (
        "@echo off\r\n"
        'cd /d "%~dp0"\r\n'
        f'start "" "{pythonw}" "%~dp0studio.py"\r\n'
    )
    with open(os.path.join(DIST, "启动桌宠工坊.bat"), "w", encoding="ascii", newline="") as f:
        f.write(launcher)

    print("打包完成:", DIST)


if __name__ == "__main__":
    main()
