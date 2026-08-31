# 🖥️ 桌宠工坊（Pet Studio）

> 让任何人 **3 分钟生成一个属于自己的 AI 桌面桌宠** —— 人设、立绘、声音、AI 大脑，四步全搞定。

桌宠工坊把完整的 AI 桌宠能力封装成一套集成软件：填写角色设定 → 上传立绘 → 提交参考音频（可选）→ 一键生成，就能得到一个具备 **对话、看屏、联网查询、记忆、语音朗读** 的专属桌面桌宠。

---

## ✨ 功能特性

| 能力 | 说明 |
|------|------|
| 🧠 **AI 对话** | 本地 Ollama 或任意 OpenAI 兼容 API，角色扮演驱动 |
| 👀 **看屏互动** | 视觉模型定时扫描屏幕，主动搭话关心你（间隔可自定义） |
| 🌐 **联网查询** | 遇到不知道的内容自动联网搜索（Bing），补全知识再回答 |
| 🧠 **一周记忆** | 本地持久化记忆，重启不「失忆」，只保留最近 7 天 |
| 🎨 **多立绘切换** | 支持多张立绘，右键一键切换；自动去背景转透明 PNG |
| 🔊 **语音朗读** | GPT-SoVITS 声音克隆：中文直读 / 日语翻译朗读（可切换、可调音量、可静音） |
| 🕒 **时间感知** | 根据当前时间自动选择问候语，不会反复说同一句「晚安」 |
| ⚡ **懒人模式** | 粘贴一段角色介绍，AI 自动提取人设字段并填表 |

---

## 📋 四步流程

```
Step 1  生成人设   →  填表单 / 粘贴文字让 AI 提取，生成角色设定
Step 2  提交立绘   →  上传多张立绘，自动去背景，可切换、可调大小
Step 3  训练声音（可选）→  提交 3~10 秒参考音频，零样本克隆音色（无需训练）
Step 4  生成桌宠   →  一键产出独立桌宠文件夹 + 启动脚本 + 桌面快捷方式
```

---

## 🚀 快速开始

### 方式一：向导 GUI（推荐）

```bash
pip install -r requirements.txt
python studio.py
```

按四步向导操作，生成完成后：

```
output/<角色名>/ 启动桌宠.bat   ← 双击即用
```

### 方式二：核心引擎（Python API）

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

### 添加声音（零样本克隆）

```python
from core.voice_clone import prepare_voice, deploy_start_tts
from core.pet_builder import build_pet

voice = prepare_voice(
    ref_audio_path="参考音频.wav",   # 3~10 秒，清晰无背景音
    ref_text="参考音频里说的话",
    ref_lang="中文",
    role_dir="output/我的助手",
)
deploy_start_tts(r"C:\...\GPT-SoVITS-v4-20250529")  # 部署通用 TTS 服务

build_pet(..., voice_config=voice)
```

---

## 📦 环境要求

| 组件 | 用途 | 必需 | 下载 |
|------|------|------|------|
| Python 3.10+ | 运行工坊与桌宠 | ✅ | python.org |
| Ollama + qwen2.5vl:7b | AI 对话 + 看屏（约 11GB） | ✅（或改用 API） | ollama.com/download，`ollama pull qwen2.5vl:7b` |
| GPT-SoVITS 整合包 | 语音合成（约 7GB） | ⚠️ 仅声音需要 | hf-mirror.com/lj1995/GPT-SoVITS-windows-package |
| 任意 OpenAI 兼容 API | 替代 Ollama 驱动对话 | 可选 | DeepSeek 等 |

> 详细安装步骤见 **`安装说明.md`**；工坊右上角「环境设置」可配置并自动检测 GPT-SoVITS / Ollama 是否就绪。

---

## 🗂️ 目录结构

```
桌宠工坊/
├── studio.py                # 向导式 GUI（四步向导）
├── core/                    # 核心引擎
│   ├── persona_gen.py       # 人设生成（表单 → persona 设定）
│   ├── extract.py           # AI 文字提取人设（懒人模式）
│   ├── portrait_proc.py     # 立绘处理（去白底 / 透明化）
│   ├── voice_clone.py       # 零样本声音克隆 + TTS 服务部署
│   ├── pet_builder.py       # 组装生成桌宠（config + 立绘 + 模板 + 快捷方式）
│   ├── studio_config.py     # 环境配置读写（GPT-SoVITS / Ollama 路径）
│   └── paths.py             # 开发 / 打包（exe）路径自适应
├── template/                # 桌宠模板代码（参数化，配置驱动）
│   ├── main_pyside6.py      # 桌宠主程序（真透明 + 气泡 + 记忆 + 语音）
│   ├── ai_client.py         # AI 客户端（Ollama / API 通用）
│   ├── search.py            # 联网搜索
│   ├── memory.py            # 7 天记忆模块
│   ├── tts_client.py        # 语音客户端（从 config 读参考音频）
│   └── requirements.txt
├── gptsovits_assets/
│   └── start_tts_user.py    # 通用零样本 TTS 服务启动脚本
├── configs/studio.json      # 本机环境配置（git 忽略，不提交）
├── output/                  # 生成的桌宠输出到这里
├── 安装说明.md               # 模型下载与放置详细说明
└── test_build.py            # 端到端测试脚本
```

---

## 🎮 生成桌宠的功能总览

生成的桌宠（`output/<角色名>/`）开箱即用，功能与艾雅法拉桌宠一致：

- **悬浮置顶** 无边框透明窗口，拖动立绘可移动
- **对话** 左键点击立绘弹出输入框；回复以头顶气泡显示
- **历史** 右键查看历史对话（本地持久化，保留 7 天）
- **看屏** 右键手动看屏 / 定时自动看屏（右键可设间隔 10~3600 秒）
- **语音** 回复自动朗读；右键切换 中文/日语翻译 模式、拖动音量滑块、一键静音
- **多立绘** 右键切换立绘；替换 `assets/` 下的图片即可换装

---

## 🧭 常见问题（FAQ）

**Q：没有 NVIDIA 显卡能跑吗？**
能。对话模型可在 CPU 上运行（速度慢一些）；语音合成也支持 CPU 模式。有 8GB 以上显存的显卡体验最佳。

**Q：用 API 的话还需要装 Ollama 吗？**
不需要。工坊第四步选「API 引擎」，填 DeepSeek / OpenAI 等任意兼容接口即可，门槛更低、不看显卡。

**Q：声音克隆用什么语言都行吗？**
可以跨语言。用日语样本克隆的音色，照样能合成中文（音色保留，可能带一点原语种腔调）。

**Q：生成桌宠需要多少磁盘空间？**
桌宠本体很小（几 MB）。大头是模型：Ollama 模型约 11GB、GPT-SoVITS 约 13GB（可选），都装在系统里，不占用桌宠目录。

---

## 📈 路线图

- [x] 桌宠模板（参数化，去除硬编码）
- [x] 人设 / 立绘 / 声音 / 生成 四大核心模块
- [x] 向导式 GUI（四步向导）
- [x] AI 文字提取人设（懒人模式）
- [x] 声音引导 + 环境检测
- [x] exe 打包（免 Python 运行工坊）
- [ ] 生成的桌宠也打包为独立 exe
- [ ] Live2D 动态立绘支持

---

## 📄 许可证

[MIT License](LICENSE) © 2026 tiandiaaa

本项目为开源学习项目，生成的桌宠形象版权归其原作者所有。
