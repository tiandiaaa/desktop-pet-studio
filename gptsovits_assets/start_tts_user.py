import os
import runpy
import sys

# 通用零样本 TTS 服务启动脚本（由桌宠工坊部署到 GPT-SoVITS 目录）。
# 用预训练模型（不指定 -s/-g，走 config.py 默认预训练），参考音频由每次合成请求传入，
# 因此一个服务可供任意角色使用，无需训练专属模型。

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# pythonw（无控制台）启动时 sys.stdout/stderr 为 None，uvicorn 写日志会崩溃；重定向到日志文件。
if sys.stdout is None or sys.stderr is None:
    _log = open(os.path.join(ROOT, "tts_server.log"), "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _log
    if sys.stderr is None:
        sys.stderr = _log

sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "GPT_SoVITS"))

sys.argv = [
    "api.py",
    "-d", "cuda",
    "-p", "9880",
]
runpy.run_path(os.path.join(ROOT, "api.py"), run_name="__main__")
