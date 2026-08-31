# -*- coding: utf-8 -*-
"""立绘处理模块：把用户上传的图片转成透明背景 PNG（自动去白底）。"""

import os
from collections import deque

import numpy as np
from PIL import Image


def remove_white_background(img, threshold=238):
    """从图片边缘扩散，把连通的白色背景变透明（保留角色内部的白色，如衣服）。

    img: PIL Image（RGBA）。返回处理后的 RGBA Image。
    """
    arr = np.array(img)
    h, w = arr.shape[:2]
    # 白色 mask（阈值放宽到 238，容忍 JPG 压缩伪影）
    white = (
        (arr[:, :, 0] > threshold)
        & (arr[:, :, 1] > threshold)
        & (arr[:, :, 2] > threshold)
    )
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()

    for x in range(w):
        if white[0, x] and not visited[0, x]:
            visited[0, x] = True
            queue.append((0, x))
        if white[h - 1, x] and not visited[h - 1, x]:
            visited[h - 1, x] = True
            queue.append((h - 1, x))
    for y in range(h):
        if white[y, 0] and not visited[y, 0]:
            visited[y, 0] = True
            queue.append((y, 0))
        if white[y, w - 1] and not visited[y, w - 1]:
            visited[y, w - 1] = True
            queue.append((y, w - 1))

    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and white[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

    arr[visited, 3] = 0
    return Image.fromarray(arr, "RGBA")


def binarize_alpha(img, threshold=128):
    """alpha 通道二值化（>=threshold 全不透明，否则全透明），消除半透明毛边。"""
    arr = np.array(img)
    a = arr[:, :, 3]
    arr[:, :, 3] = np.where(a >= threshold, 255, 0)
    return Image.fromarray(arr, "RGBA")


def has_transparency(img):
    """判断图片是否已有透明区域（alpha 最小值 < 250）。"""
    arr = np.array(img)
    if arr.shape[2] < 4:
        return False
    return bool((arr[:, :, 3] < 250).any())


def process_portrait(src_path, out_path, remove_bg=True, threshold=238):
    """处理单张立绘：转 RGBA，去白底（可选），二值化 alpha，保存为 PNG。

    返回 (out_path, did_remove_bg)。
    """
    img = Image.open(src_path).convert("RGBA")
    did_remove = False
    if remove_bg and not has_transparency(img):
        img = remove_white_background(img, threshold=threshold)
        did_remove = True
    img = binarize_alpha(img)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "PNG")
    return out_path, did_remove
