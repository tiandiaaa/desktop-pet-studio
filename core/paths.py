# -*- coding: utf-8 -*-
"""路径工具：区分「开发模式」与「PyInstaller 打包后」，正确找到资源与输出目录。

- resource_dir()：只读资源（template、gptsovits_assets、安装说明等）。
  打包后指向 exe 内部的 _MEIPASS 解压目录；开发时指向本项目目录。
- app_dir()：可读写目录（output、configs）。
  打包后指向 exe 所在目录；开发时指向本项目目录。
"""

import os
import sys


def _is_frozen():
    return bool(getattr(sys, "frozen", False))


def resource_dir():
    if _is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def app_dir():
    if _is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
