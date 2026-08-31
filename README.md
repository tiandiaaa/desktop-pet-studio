# 桌宠工坊（Pet Studio）

让任何人都能**生成自己的专属桌面桌宠**。

## 四步流程

```
Step 1 生成人设  →  填写角色表单，生成 persona 设定
Step 2 提交立绘  →  上传多张立绘，自动去背景，可切换
Step 3 训练声音（可选）→  提交参考音频，零样本克隆音色（无需训练）
Step 4 生成桌宠  →  一键产出独立桌宠文件夹 + 启动脚本 + 桌面快捷方式
```

## 目录结构

```
桌宠工坊/
├── studio.py              # 向导式 GUI（开发中）
├── core/                  # 核心引擎（已完成）
│   ├── persona_gen.py     # 人设生成
│   ├── portrait_proc.py   # 立绘处理（去背景转透明）
│   ├── voice_clone.py     # 零样本声音克隆
│   └── pet_builder.py     # 组装生成桌宠
├── template/              # 桌宠模板代码（参数化后）
│   ├── main_pyside6.py    # 桌宠主程序（真透明 + 气泡 + 记忆 + 语音）
│   ├── ai_client.py       # AI 客户端（Ollama / API 通用）
│   ├── search.py          # 联网搜索
│   ├── memory.py          # 7 天记忆
│   ├── tts_client.py      # 语音客户端（从 config 读参考音频）
│   └── requirements.txt
├── gptsovits_assets/
│   └── start_tts_user.py  # 通用零样本 TTS 服务启动脚本
├── output/                # 生成的桌宠输出到这里
└── test_build.py          # 端到端测试脚本
```

## 核心引擎用法（当前可用）

在没有 GUI 前，可以直接用 Python 调用核心引擎生成桌宠：

```python
from core.persona_gen import build_persona
from core.pet_builder import build_pet

persona = build_persona({
    "name": "我的助手",
    "user_addr": "主人",
    "appearance": "粉色长发、穿白色裙子",
    "background": "一名可爱的助手少女",
    "personality": "温柔、活泼",
    "speech_style": "称呼对方「主人」，句尾带「~」",
})

pet_dir = build_pet(
    role_name="我的助手",
    persona_text=persona,
    portraits=[{"src": "立绘1.png", "width": 320}],
)
```

生成的桌宠在 `output/我的助手/`，双击 `启动桌宠.bat` 即可运行。

## 声音（零样本克隆）

```python
from core.voice_clone import prepare_voice, deploy_start_tts
from core.pet_builder import build_pet

voice = prepare_voice(
    ref_audio_path="参考音频.wav",   # 3~10 秒
    ref_text="参考音频里说的话",
    ref_lang="中文",
    role_dir="output/我的助手",
)
deploy_start_tts(r"C:\...\GPT-SoVITS-v4-20250529")  # 部署通用 TTS 服务

build_pet(..., voice_config=voice)
```

零样本克隆用 GPT-SoVITS 的预训练模型，无需训练，几分钟出结果。

> **GUI 里已内置声音引导**：向导右上角「环境设置」可配置 GPT-SoVITS 整合包路径并自动检测是否就绪；「安装说明」按钮提供下载链接与放置位置。

## 模型安装（GPT-SoVITS + Ollama）

语音合成和对话需要两样「大脑」，安装位置见 **`安装说明.md`**（工坊里点「安装说明」按钮也可查看）：

| 组件 | 用途 | 下载 | 放置 |
|------|------|------|------|
| GPT-SoVITS 整合包 | 语音合成（约 7GB，可选） | hf-mirror.com/lj1995/GPT-SoVITS-windows-package | 解压到任意位置，在「环境设置」里指定目录 |
| Ollama + qwen2.5vl:7b | 对话 + 看屏（约 11GB） | ollama.com/download | 安装后 `ollama pull qwen2.5vl:7b` |

## 当前状态

- [x] 桌宠模板（参数化，去除艾雅法拉硬编码）
- [x] 人设生成模块
- [x] 立绘处理模块
- [x] 零样本声音克隆模块
- [x] 桌宠生成模块
- [x] 向导式 GUI（studio.py，四步向导）
- [x] 声音引导 + 环境设置（GPT-SoVITS 路径检测）
- [x] 模型安装说明（安装说明.md）
- [x] 端到端测试（人设 → 立绘 → 生成桌宠）
- [ ] 打包分发（exe）
