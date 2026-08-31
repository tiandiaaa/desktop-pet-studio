# -*- coding: utf-8 -*-
"""桌宠工坊 向导式 GUI 主程序：四步生成专属桌面桌宠。"""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTextEdit, QPushButton, QStackedWidget, QFileDialog, QListWidget,
    QSpinBox, QCheckBox, QComboBox, QMessageBox, QGroupBox, QFormLayout,
    QDialog, QDialogButtonBox, QScrollArea,
)

from core.persona_gen import build_persona
from core.pet_builder import build_pet, create_desktop_shortcut
from core.voice_clone import prepare_voice, deploy_start_tts
from core.studio_config import load_config, save_config, check_gptsovits, check_ollama
from core.paths import app_dir, resource_dir


class Step1Persona(QWidget):
    """第一步：人设。"""

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        lay = QVBoxLayout(content)

        lay.addWidget(QLabel("填写角色的人设，越具体越有灵魂。带 * 为必填。"))

        # 懒人模式：粘贴文字 → AI 自动提取
        raw_group = QGroupBox("懒人模式：粘贴角色文字，AI 自动提取")
        raw_lay = QVBoxLayout(raw_group)
        self.raw_text = QTextEdit()
        self.raw_text.setPlaceholderText(
            "把角色介绍、档案、设定文整段粘进来，点「AI 自动提取」自动填表（也可以不粘，直接手动填）"
        )
        self.raw_text.setFixedHeight(64)
        raw_lay.addWidget(self.raw_text)
        self.extract_btn = QPushButton("AI 自动提取")
        self.extract_btn.clicked.connect(self._on_extract)
        raw_lay.addWidget(self.extract_btn)
        lay.addWidget(raw_group)

        form = QFormLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("例如：小星")
        self.user_addr = QLineEdit("主人")
        self.user_addr.setPlaceholderText("角色怎么称呼你，例如：主人 / 前辈")

        form.addRow("角色名 *", self.name)
        form.addRow("称呼你为", self.user_addr)
        lay.addLayout(form)

        self.appearance = self._add_area(lay, "外观（长相、发型、服装等）")
        self.background = self._add_area(lay, "身份背景（出身、职业、经历等）")
        self.body = self._add_area(lay, "身体与设定（疾病、特殊能力、宠物等，可留空）")
        self.personality = self._add_area(lay, "性格 *")
        self.speech_style = self._add_area(lay, "说话风格 *（语气、称呼、口头禅等）")
        self.interaction = self._add_area(lay, "交流规则（可选，如沉默时主动搭话）")
        self.worldview = self._add_area(lay, "世界观（可选，如架空世界设定）")

        self.personality.setPlaceholderText("例如：温柔、活泼、有点迷糊")
        self.speech_style.setPlaceholderText("例如：称呼对方「主人」，句尾常带「~」，语气软糯")

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _add_area(self, lay, label):
        lab = QLabel(label)
        lab.setStyleSheet("font-weight:500; margin-top:6px;")
        area = QTextEdit()
        area.setFixedHeight(52)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # 内容多时显示内部滚动条
        lay.addWidget(lab)
        lay.addWidget(area)
        return area

    def fields(self):
        return {
            "name": self.name.text(),
            "user_addr": self.user_addr.text(),
            "appearance": self.appearance.toPlainText(),
            "background": self.background.toPlainText(),
            "body": self.body.toPlainText(),
            "personality": self.personality.toPlainText(),
            "speech_style": self.speech_style.toPlainText(),
            "interaction": self.interaction.toPlainText(),
            "worldview": self.worldview.toPlainText(),
        }

    def set_extract_callback(self, cb):
        self._extract_cb = cb

    def _on_extract(self):
        if self._extract_cb:
            self._extract_cb()


class Step2Portrait(QWidget):
    """第二步：立绘（可多张，用于切换）。"""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel("上传立绘（支持多张，右键桌宠可切换）。建议透明背景 PNG；白底图会自动去背景。"))

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("添加立绘")
        self.add_btn.clicked.connect(self._add)
        self.remove_btn = QPushButton("移除选中")
        self.remove_btn.clicked.connect(self._remove)
        btn_row.addWidget(self.add_btn)
        btn_row.addWidget(self.remove_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        self.list = QListWidget()
        lay.addWidget(self.list)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("立绘显示宽度："))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(120, 800)
        self.width_spin.setValue(360)
        self.width_spin.setSuffix(" px")
        size_row.addWidget(self.width_spin)
        size_row.addStretch(1)
        lay.addLayout(size_row)

        self._paths = []

    def _add(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择立绘", "",
            "图片 (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        for f in files:
            if f and f not in self._paths:
                self._paths.append(f)
                self.list.addItem(os.path.basename(f))

    def _remove(self):
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
            self._paths.pop(row)

    def portraits(self):
        return [{"src": p, "width": self.width_spin.value()} for p in self._paths]


class Step3Voice(QWidget):
    """第三步：声音（可选，零样本克隆）。"""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)

        self.enable = QCheckBox("启用语音（零样本克隆，无需训练）")
        self.enable.toggled.connect(self._toggle)
        lay.addWidget(self.enable)

        # 语音环境状态
        env_box = QGroupBox("语音环境")
        env_lay = QVBoxLayout(env_box)
        self.env_status = QLabel()
        env_hint = QLabel(
            "语音合成需要 GPT-SoVITS 整合包。请点击右上角「环境设置」指定它的位置；"
            "若还没下载，见「安装说明」里的下载链接。参考音频建议 3~10 秒 wav。"
        )
        env_hint.setWordWrap(True)
        env_lay.addWidget(self.env_status)
        env_lay.addWidget(env_hint)
        lay.addWidget(env_box)
        self._refresh_env()

        self.box = QGroupBox("参考音频设置")
        box_lay = QFormLayout(self.box)

        row = QHBoxLayout()
        self.ref_path = QLineEdit()
        self.ref_path.setPlaceholderText("选择一段 3~10 秒的 wav 参考音频")
        browse = QPushButton("浏览")
        browse.clicked.connect(self._browse)
        row.addWidget(self.ref_path)
        row.addWidget(browse)
        box_lay.addRow("参考音频", row)

        self.ref_text = QLineEdit()
        self.ref_text.setPlaceholderText("音频里说的内容（可选，有则更准）")
        box_lay.addRow("参考文本", self.ref_text)

        self.ref_lang = QComboBox()
        self.ref_lang.addItems(["中文", "日文", "英文"])
        box_lay.addRow("语种", self.ref_lang)

        self.speed = QSpinBox()
        self.speed.setRange(50, 150)
        self.speed.setValue(85)
        self.speed.setSuffix(" %")
        box_lay.addRow("语速", self.speed)

        lay.addWidget(self.box)
        lay.addStretch(1)
        self._toggle(False)

    def _browse(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择参考音频", "", "音频 (*.wav *.mp3)")
        if f:
            self.ref_path.setText(f)

    def _toggle(self, checked):
        self.box.setEnabled(checked)

    def _refresh_env(self):
        cfg = load_config()
        ok, msg = check_gptsovits(cfg.get("gptsovits_dir", ""))
        if ok:
            self.env_status.setText("GPT-SoVITS：✓ 已就绪")
            self.env_status.setStyleSheet("color:#1d9e75; font-weight:500;")
        else:
            self.env_status.setText("GPT-SoVITS：✗ 未找到（" + msg + "）")
            self.env_status.setStyleSheet("color:#e24b4a; font-weight:500;")

    def is_enabled(self):
        return self.enable.isChecked()

    def ref_audio(self):
        return self.ref_path.text().strip()


class Step4Generate(QWidget):
    """第四步：AI 引擎与生成。"""

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel("选择驱动对话的 AI 引擎，然后点击生成。"))

        self.engine = QComboBox()
        self.engine.addItems(["本地 Ollama（免费离线）", "API（DeepSeek 等）"])
        self.engine.currentIndexChanged.connect(self._toggle_engine)
        lay.addWidget(self.engine)

        # Ollama 配置
        self.ollama_box = QGroupBox("本地 Ollama")
        of = QFormLayout(self.ollama_box)
        self.o_model = QLineEdit("qwen2.5vl:7b")
        of.addRow("模型（含视觉）", self.o_model)
        self.o_base = QLineEdit("http://localhost:11434/v1")
        of.addRow("服务地址", self.o_base)
        lay.addWidget(self.ollama_box)

        # API 配置
        self.api_box = QGroupBox("API")
        af = QFormLayout(self.api_box)
        self.a_base = QLineEdit("https://api.deepseek.com/v1")
        self.a_key = QLineEdit()
        self.a_key.setPlaceholderText("填写 API Key")
        self.a_model = QLineEdit("deepseek-chat")
        self.a_vision = QLineEdit()
        self.a_vision.setPlaceholderText("视觉模型（可选，留空则无看屏）")
        af.addRow("Base URL", self.a_base)
        af.addRow("API Key", self.a_key)
        af.addRow("模型", self.a_model)
        af.addRow("视觉模型", self.a_vision)
        lay.addWidget(self.api_box)

        # 桌宠行为
        behav = QGroupBox("桌宠行为")
        bf = QFormLayout(behav)
        self.watch = QCheckBox("自动看屏并搭话")
        self.watch.setChecked(True)
        self.interval = QSpinBox()
        self.interval.setRange(5, 600)
        self.interval.setValue(25)
        self.interval.setSuffix(" 秒")
        self.search = QCheckBox("允许联网查资料")
        self.search.setChecked(True)
        bf.addRow(self.watch)
        bf.addRow("看屏间隔", self.interval)
        bf.addRow(self.search)
        lay.addWidget(behav)

        lay.addStretch(1)
        self._toggle_engine(0)

    def _toggle_engine(self, idx):
        self.ollama_box.setVisible(idx == 0)
        self.api_box.setVisible(idx == 1)

    def ai_config(self):
        if self.engine.currentIndex() == 0:
            return {
                "base_url": self.o_base.text().strip(),
                "api_key": "ollama",
                "model": self.o_model.text().strip(),
                "vision_model": self.o_model.text().strip(),
                "temperature": 0.9,
                "max_history": 20,
                "keep_alive": "30m",
            }
        return {
            "base_url": self.a_base.text().strip(),
            "api_key": self.a_key.text().strip(),
            "model": self.a_model.text().strip(),
            "vision_model": self.a_vision.text().strip(),
            "temperature": 0.9,
            "max_history": 20,
            "keep_alive": "30m",
        }

    def pet_opts(self):
        return {
            "auto_watch_screen": self.watch.isChecked(),
            "screenshot_interval_sec": self.interval.value(),
            "search_enabled": self.search.isChecked(),
            "search_max": 5,
        }


class StudioWindow(QWidget):
    extract_done = Signal(dict)  # AI 提取结果 → 主线程

    def __init__(self):
        super().__init__()
        self.setWindowTitle("桌宠工坊 · 生成你的专属桌面桌宠")
        self.resize(680, 640)

        lay = QVBoxLayout(self)
        head = QHBoxLayout()
        title = QLabel("桌宠工坊")
        title.setStyleSheet("font-size:18px; font-weight:500;")
        head.addWidget(title)
        head.addStretch(1)
        env_btn = QPushButton("环境设置")
        env_btn.clicked.connect(self._open_env)
        help_btn = QPushButton("安装说明")
        help_btn.clicked.connect(self._open_help)
        head.addWidget(env_btn)
        head.addWidget(help_btn)
        lay.addLayout(head)

        self.steps = QStackedWidget()
        self.step1 = Step1Persona()
        self.step1.set_extract_callback(self._do_extract)
        self.extract_done.connect(self._fill_extracted)
        self.step2 = Step2Portrait()
        self.step3 = Step3Voice()
        self.step4 = Step4Generate()
        for s in (self.step1, self.step2, self.step3, self.step4):
            self.steps.addWidget(s)
        lay.addWidget(self.steps, 1)

        nav = QHBoxLayout()
        self.back_btn = QPushButton("上一步")
        self.next_btn = QPushButton("下一步")
        self.gen_btn = QPushButton("生成桌宠")
        self.back_btn.clicked.connect(self._back)
        self.next_btn.clicked.connect(self._next)
        self.gen_btn.clicked.connect(self._generate)
        nav.addWidget(self.back_btn)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        nav.addWidget(self.gen_btn)
        lay.addLayout(nav)

        self._update_nav()

    def _update_nav(self):
        idx = self.steps.currentIndex()
        self.back_btn.setEnabled(idx > 0)
        self.next_btn.setVisible(idx < 3)
        self.gen_btn.setVisible(idx == 3)

    def _back(self):
        self.steps.setCurrentIndex(self.steps.currentIndex() - 1)
        self._update_nav()

    def _next(self):
        if self.steps.currentIndex() == 0:
            if not self.step1.name.text().strip():
                QMessageBox.warning(self, "提示", "请先填写角色名")
                return
            if not self.step1.personality.toPlainText().strip():
                QMessageBox.warning(self, "提示", "请填写性格")
                return
        if self.steps.currentIndex() == 1:
            if not self.step2.portraits():
                QMessageBox.warning(self, "提示", "请至少添加一张立绘")
                return
        self.steps.setCurrentIndex(self.steps.currentIndex() + 1)
        self._update_nav()

    def _generate(self):
        fields = self.step1.fields()
        role_name = fields["name"].strip()
        portraits = self.step2.portraits()
        if not role_name or not portraits:
            QMessageBox.warning(self, "提示", "角色名和立绘不能为空")
            return

        output_root = os.path.join(app_dir(), "output")
        role_dir = os.path.join(output_root, role_name)

        # 声音（可选）
        voice_config = None
        if self.step3.is_enabled() and self.step3.ref_audio():
            try:
                voice_config = prepare_voice(
                    ref_audio_path=self.step3.ref_audio(),
                    ref_text=self.step3.ref_text.text(),
                    ref_lang=self.step3.ref_lang.currentText(),
                    role_dir=role_dir,
                    speed=self.step3.speed.value() / 100.0,
                )
                gptsovits = DEFAULT_STUDIO_CFG["gptsovits_dir"]
                if os.path.isdir(gptsovits):
                    deploy_start_tts(gptsovits)
            except Exception as e:
                QMessageBox.warning(self, "声音处理失败", str(e))
                voice_config = None

        try:
            persona = build_persona(fields)
            pet_dir = build_pet(
                role_name=role_name,
                persona_text=persona,
                portraits=portraits,
                ai_config=self.step4.ai_config(),
                voice_config=voice_config,
                pet_opts=self.step4.pet_opts(),
            )
            lnk = create_desktop_shortcut(pet_dir, role_name)
        except Exception as e:
            QMessageBox.critical(self, "生成失败", str(e))
            return

        msg = f"桌宠已生成：\n{pet_dir}\n\n双击「启动桌宠.bat」即可运行。"
        if lnk:
            msg += "\n\n已在桌面创建快捷方式。"
        QMessageBox.information(self, "完成", msg)

    def _do_extract(self):
        text = self.step1.raw_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请先粘贴角色文字")
            return
        ai_cfg = self.step4.ai_config()
        base_url = ai_cfg.get("base_url", "")
        api_key = ai_cfg.get("api_key", "")
        model = ai_cfg.get("model", "")
        if "localhost" in base_url or "127.0.0.1" in base_url:
            from core.studio_config import check_ollama
            if not check_ollama(base_url):
                QMessageBox.warning(self, "提示", "本地 Ollama 未连接，请先在右上角「环境设置」确认地址")
                return
        elif not api_key.strip():
            QMessageBox.warning(self, "提示", "请在第四步填写 API Key")
            return
        self.step1.extract_btn.setEnabled(False)
        self.step1.extract_btn.setText("AI 提取中…（约 10~20 秒）")
        threading.Thread(target=self._extract_worker, args=(text, base_url, api_key, model), daemon=True).start()

    def _extract_worker(self, text, base_url, api_key, model):
        from core.extract import extract_fields
        result = extract_fields(text, base_url, api_key, model)
        self.extract_done.emit(result)

    def _fill_extracted(self, result):
        self.step1.extract_btn.setEnabled(True)
        self.step1.extract_btn.setText("AI 自动提取")
        if not result:
            QMessageBox.warning(self, "提取失败", "没提取到内容。请确认 AI 引擎可用（本地 Ollama 在线 / API Key 正确），或手动填写。")
            return
        s = self.step1
        mapping = {
            "name": s.name,
            "user_addr": s.user_addr,
            "appearance": s.appearance,
            "background": s.background,
            "body": s.body,
            "personality": s.personality,
            "speech_style": s.speech_style,
            "interaction": s.interaction,
            "worldview": s.worldview,
        }
        filled = 0
        for key, widget in mapping.items():
            val = (result.get(key) or "").strip()
            if val:
                widget.setText(val)
                filled += 1
        if filled == 0:
            QMessageBox.warning(self, "提取失败", "AI 没识别出有效字段，请调整文字或手动填写。")
            return
        QMessageBox.information(self, "提取完成", f"已自动填充 {filled} 个字段，可继续微调。")

    def _open_env(self):
        dlg = EnvDialog(self)
        if dlg.exec():
            self.step3._refresh_env()

    def _open_help(self):
        path = os.path.join(resource_dir(), "安装说明.md")
        if os.path.isfile(path):
            try:
                os.startfile(path)
                return
            except Exception:
                pass
        QMessageBox.information(self, "安装说明", HELP_TEXT)


class EnvDialog(QDialog):
    """环境设置：配置 GPT-SoVITS 整合包路径与 Ollama 地址。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("环境设置")
        self.resize(560, 400)
        lay = QVBoxLayout(self)

        cfg = load_config()

        g = QGroupBox("GPT-SoVITS 整合包（语音合成，可选）")
        gl = QFormLayout(g)
        row = QHBoxLayout()
        self.gptsovits = QLineEdit(cfg.get("gptsovits_dir", ""))
        browse = QPushButton("浏览")
        browse.clicked.connect(self._browse)
        row.addWidget(self.gptsovits)
        row.addWidget(browse)
        gl.addRow("整合包目录", row)
        self.g_status = QLabel()
        gl.addRow("状态", self.g_status)
        dl = QLabel("下载：https://hf-mirror.com/lj1995/GPT-SoVITS-windows-package")
        dl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        gl.addRow("", dl)
        lay.addWidget(g)

        o = QGroupBox("本地模型 Ollama（对话 + 看屏）")
        ol = QFormLayout(o)
        self.ollama = QLineEdit(cfg.get("ollama_base_url", "http://localhost:11434"))
        ol.addRow("服务地址", self.ollama)
        self.o_status = QLabel()
        ol.addRow("状态", self.o_status)
        lay.addWidget(o)

        hint = QLabel("详细下载与安装步骤见「安装说明.md」。")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self._refresh()

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择 GPT-SoVITS 整合包目录")
        if d:
            self.gptsovits.setText(d)
            self._refresh()

    def _refresh(self):
        ok, msg = check_gptsovits(self.gptsovits.text().strip())
        self.g_status.setText("✓ 已就绪" if ok else ("✗ " + msg))
        self.g_status.setStyleSheet("color:#1d9e75;" if ok else "color:#e24b4a;")
        ok2 = check_ollama(self.ollama.text().strip())
        self.o_status.setText("✓ 在线" if ok2 else "✗ 未连接")
        self.o_status.setStyleSheet("color:#1d9e75;" if ok2 else "color:#e24b4a;")

    def _save(self):
        cfg = load_config()
        cfg["gptsovits_dir"] = self.gptsovits.text().strip()
        cfg["ollama_base_url"] = self.ollama.text().strip()
        save_config(cfg)
        self.accept()


HELP_TEXT = (
    "【GPT-SoVITS 整合包】（语音合成，约 7GB，可选）\n"
    "下载：https://hf-mirror.com/lj1995/GPT-SoVITS-windows-package\n"
    "放置：解压到任意位置，然后在「环境设置」里选择解压后的目录"
    "（即包含 api.py 的那一层）。\n\n"
    "【本地模型 Ollama】（对话 + 看屏，约 11GB）\n"
    "下载：https://ollama.com/download\n"
    "安装后命令行执行：ollama pull qwen2.5vl:7b\n"
    "并确认「环境设置」里服务地址为 http://localhost:11434\n\n"
    "如果不想装本地模型，也可在「AI 引擎」里改用 API（如 DeepSeek）。"
)


def main():
    app = QApplication(sys.argv)
    win = StudioWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
