import io
import json
import os
import re
import sys
import threading
import time

from PySide6.QtCore import Qt, QTimer, QRect, QPoint, Signal, QUrl
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QPainterPath, QFontMetrics
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QTextEdit, QMenu, QDialog, QSlider, QInputDialog,
)

from PIL import Image, ImageGrab

from ai_client import AIClient
from search import web_search, format_results
from memory import load_memory, save_memory
from tts_client import TTSClient, translate_zh_to_ja

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUBBLE_W = 260
BUBBLE_GAP = 4  # 气泡与立绘之间的垂直间距


def _p(*parts):
    return os.path.join(BASE_DIR, *parts)


class BubbleWidget(QWidget):
    """头顶气泡：圆角矩形 + 尾巴 + 文字，用 QPainter 绘制。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._font = QFont("Microsoft YaHei", 10)
        self._fm = QFontMetrics(self._font)  # 缓存，避免重复创建
        self.setFixedWidth(BUBBLE_W)
        self.set_text("前辈，我在哦~")

    def set_text(self, text):
        # 相同文字跳过，减少无谓重绘
        if text == self._text:
            return
        self._text = text
        r = self._fm.boundingRect(QRect(0, 0, BUBBLE_W - 36, 10000), Qt.TextWordWrap, text)
        self.setFixedHeight(r.height() + 48)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        body_h = self.height() - 14
        path = QPainterPath()
        path.addRoundedRect(2, 2, w - 4, body_h - 2, 14, 14)
        p.fillPath(path, QColor("#ffffff"))
        p.setPen(QColor("#dcdcdc"))
        p.drawPath(path)
        cx = w // 2
        tail = QPainterPath()
        tail.moveTo(cx - 9, body_h - 2)
        tail.lineTo(cx + 9, body_h - 2)
        tail.lineTo(cx, body_h + 12)
        tail.closeSubpath()
        p.fillPath(tail, QColor("#ffffff"))
        p.setPen(QColor("#333333"))
        p.setFont(self._font)
        p.drawText(QRect(16, 14, w - 32, body_h - 20),
                   Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self._text)
        p.end()


class EyjaPet(QWidget):
    """立绘主窗口（立绘 + 输入框）；气泡为独立置顶窗口，减小重绘面积。"""

    # 后台线程 → 主线程 的跨线程信号（QTimer.singleShot 在后台线程不会执行，必须用信号）
    reply_ready = Signal(str)     # 收到回复文本（对话）
    watch_reply = Signal(str)     # 看屏评论（单独信号，方便控制是否朗读）
    bubble_update = Signal(str)   # 更新气泡提示（如「我去查一下…」）
    error_occurred = Signal(str)  # 出错信息
    play_audio = Signal(str)      # 播放语音（音频文件路径）

    def __init__(self, config_name="config.json"):
        super().__init__()
        self._config_name = config_name
        self.cfg = self._load_json(_p(config_name))
        self.persona = self._load_text(_p("persona.txt"))
        self.client = AIClient(_p(config_name))
        self.search_enabled = self.cfg.get("search", {}).get("enabled", False)
        self.search_max = self.cfg.get("search", {}).get("max_results", 5)
        self.vision_enabled = bool(self.cfg["ai"].get("vision_model"))
        self.portraits = self._load_portraits()
        self.current_portrait_idx = 0
        # 记忆模块：加载最近 7 天的聊天（history 用于 AI 上下文，chat_log 用于界面显示）
        self._mem_history, self.chat_log = load_memory()
        self.history = [{"role": "system", "content": self._build_persona()}] + self._mem_history
        self.input_visible = False
        self.history_window = None
        self._drag_offset = None
        self._drag_moved = False
        self._watching = False
        self._pending_pos = None

        # 语音状态：模式（中文/日语翻译）、音量、静音
        self.voice_mode = "zh"   # "zh"=中文直接合成 / "ja"=先翻日语再合成
        self.volume = 1.0        # 0.0 ~ 1.0
        self.muted = False
        self.watch_speech = False  # 看屏评论是否朗读（默认关）
        self.tts = TTSClient()

        self._setup_window()
        self._setup_bubble_window()
        self._setup_ui()
        self._setup_audio()

        # 拖拽节流：最多 60fps 更新位置，减少重绘
        self._move_timer = QTimer(self)
        self._move_timer.setSingleShot(True)
        self._move_timer.timeout.connect(self._apply_pending_move)

        self.watch_interval = self.cfg["pet"].get("screenshot_interval_sec", 60)
        if self.cfg["pet"].get("auto_watch_screen", True) and self.vision_enabled:
            self.watch_timer = QTimer(self)
            self.watch_timer.timeout.connect(self._auto_watch)
            self.watch_timer.start(self.watch_interval * 1000)

        # 连接跨线程信号（信号会安全地调度到主线程执行）
        self.reply_ready.connect(self._on_reply)
        self.watch_reply.connect(self._on_watch_reply)
        self.bubble_update.connect(self.set_bubble)
        self.error_occurred.connect(self._show_error)
        self.play_audio.connect(self._play_audio)

        # 预加载模型：后台触发一次简短请求，让模型提前进显存，避免首次交互卡顿
        threading.Thread(target=self._warm_up, daemon=True).start()

    # ---- 加载 ----
    def _load_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_text(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _build_persona(self):
        persona = self.persona
        if self.search_enabled:
            persona += (
                "\n\n【联网查询】如果你遇到不确定的、需要查证的事实，"
                "或者想知道最近的实时信息，可以输出 [[SEARCH:查询关键词]] 请求联网查询，"
                "我会把查到的结果告诉你，你再结合结果回答。"
            )
        return persona

    def _load_portraits(self):
        pc = self.cfg.get("portraits")
        if pc:
            return pc
        w = self.cfg.get("pet", {}).get("portrait_width", 360)
        return [{"file": "eyja.png", "width": w}]

    # ---- 窗口 ----
    def _setup_window(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - 380, screen.bottom() - 560)

    def _setup_bubble_window(self):
        # 独立气泡窗口：文字频繁更新时只重绘这一小块，不拖累立绘
        self.bubble_win = QWidget(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.bubble_win.setAttribute(Qt.WA_TranslucentBackground)
        self.bubble_win.setAttribute(Qt.WA_NoSystemBackground)
        self.bubble_win.setAttribute(Qt.WA_TransparentForMouseEvents)
        bl = QVBoxLayout(self.bubble_win)
        bl.setContentsMargins(0, 0, 0, 0)
        self.bubble = BubbleWidget(self.bubble_win)
        bl.addWidget(self.bubble)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.portrait = QLabel(self)
        self._apply_portrait()
        self.portrait.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(self.portrait, 0, Qt.AlignHCenter)

        self.input_widget = QWidget(self)
        self.input_widget.setFixedWidth(self._pixmap.width())
        self.input_widget.setStyleSheet("background-color: white;")
        il = QHBoxLayout(self.input_widget)
        il.setContentsMargins(10, 6, 6, 6)
        il.setSpacing(6)
        self.entry = QLineEdit(self.input_widget)
        self.entry.setPlaceholderText("对艾雅法拉说些什么~")
        self.entry.setStyleSheet("border: none; background: transparent; font-size: 13px;")
        self.entry.returnPressed.connect(self.send)
        self.send_btn = QPushButton("发送", self.input_widget)
        self.send_btn.setStyleSheet(
            "background: #e8e8e8; border: none; border-radius: 6px; padding: 4px 10px;"
        )
        self.send_btn.clicked.connect(self.send)
        il.addWidget(self.entry)
        il.addWidget(self.send_btn)
        self.input_widget.hide()
        layout.addWidget(self.input_widget, 0, Qt.AlignHCenter)

        self.setLayout(layout)

    def _apply_portrait(self):
        pc = self.portraits[self.current_portrait_idx]
        pixmap = QPixmap(_p("assets", pc.get("file", "eyja.png")))
        w = pc.get("width", 360)
        pixmap = pixmap.scaledToWidth(w, Qt.SmoothTransformation)
        self.portrait.setPixmap(pixmap)
        self._pixmap = pixmap

    def _setup_audio(self):
        """初始化音频播放器（QSoundEffect，支持音量控制）。"""
        self.sound_effect = QSoundEffect(self)
        self._audio_seq = 0  # 音频临时文件序号，避免同文件覆盖冲突

    def _speak_worker(self, text):
        """后台线程：合成语音并交给主线程播放。"""
        if self.muted or not self.tts.is_ready():
            return
        try:
            if self.voice_mode == "ja":
                # 先翻译成日语，再用日语合成
                text = translate_zh_to_ja(text, self.client)
                lang = "日文"
            else:
                lang = "中文"
            audio = self.tts.synthesize(text, lang)
            if audio:
                self._audio_seq += 1
                tmp = os.path.join(BASE_DIR, f"temp_tts_{self._audio_seq}.wav")
                with open(tmp, "wb") as f:
                    f.write(audio)
                self.play_audio.emit(tmp)
        except Exception:
            pass

    def _play_audio(self, path):
        """主线程：播放音频，应用当前音量/静音设置。"""
        try:
            self.sound_effect.stop()
            self.sound_effect.setSource(QUrl.fromLocalFile(path))
            self.sound_effect.setVolume(0.0 if self.muted else self.volume)
            self.sound_effect.play()
            # 播放结束后清理临时文件
            QTimer.singleShot(8000, lambda: self._cleanup_audio(path))
        except Exception:
            pass

    def _cleanup_audio(self, path):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    def _set_voice_mode(self, mode):
        self.voice_mode = mode
        self.set_bubble("现在用中文说话哦~" if mode == "zh" else "现在会说日语啦~")

    def _set_volume(self, vol):
        self.volume = vol
        self.muted = False

    def _toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.sound_effect.stop()
            self.set_bubble("（已静音）")
        else:
            self.set_bubble("（已取消静音）")

    def _show_volume_slider(self):
        """弹出音量调节滑块弹窗（条状拖动样式）。"""
        dlg = QDialog(self)
        dlg.setWindowTitle("音量调节")
        dlg.setFixedSize(320, 60)
        layout = QHBoxLayout(dlg)
        layout.setContentsMargins(12, 8, 12, 8)

        icon_label = QLabel("🔊", dlg)
        icon_label.setFixedWidth(28)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon_label)

        slider = QSlider(Qt.Horizontal, dlg)
        slider.setRange(0, 100)
        slider.setValue(int(self.volume * 100))
        layout.addWidget(slider)

        pct_label = QLabel(f"{int(self.volume*100)}%", dlg)
        pct_label.setFixedWidth(40)
        pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(pct_label)

        def on_change(val):
            self._set_volume(val / 100)
            pct_label.setText(f"{val}%")
            if val == 0:
                icon_label.setText("🔇")
            elif val < 50:
                icon_label.setText("🔈")
            else:
                icon_label.setText("🔊")

        slider.valueChanged.connect(on_change)
        dlg.exec()

    def _sync_bubble(self):
        """把气泡窗口对齐到立绘窗口正上方居中。"""
        pw = self.width()
        bw = self.bubble_win.width()
        bx = self.x() + (pw - bw) // 2
        by = self.y() - self.bubble_win.height() - BUBBLE_GAP
        self.bubble_win.move(bx, by)

    # ---- 鼠标交互 ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_moved = False
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_offset is not None:
            self._drag_moved = True
            self._pending_pos = event.globalPosition().toPoint() - self._drag_offset
            if not self._move_timer.isActive():
                self._move_timer.start(16)
        event.accept()

    def _apply_pending_move(self):
        if self._pending_pos is not None:
            self.move(self._pending_pos)
            self._sync_bubble()
            self._pending_pos = None

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._drag_moved:
                self._toggle_input()
            self._drag_offset = None
            self._drag_moved = False
            # 确保最终位置已应用
            if self._pending_pos is not None:
                self._apply_pending_move()
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("查看历史对话", self._open_history)
        if len(self.portraits) > 1:
            menu.addAction("切换立绘", self._switch_portrait)
        if self.vision_enabled:
            menu.addAction("现在看看桌面", self.take_screenshot_now)
        menu.addAction("置顶开关", self._toggle_topmost)
        menu.addSeparator()

        # 语音模式切换
        voice_menu = menu.addMenu("语音模式")
        act_zh = voice_menu.addAction("中文")
        act_zh.setCheckable(True)
        act_zh.setChecked(self.voice_mode == "zh")
        act_zh.triggered.connect(lambda: self._set_voice_mode("zh"))
        act_ja = voice_menu.addAction("日语（翻译）")
        act_ja.setCheckable(True)
        act_ja.setChecked(self.voice_mode == "ja")
        act_ja.triggered.connect(lambda: self._set_voice_mode("ja"))

        # 音量调节（弹条状滑块）
        vol_menu = menu.addMenu("音量")
        act_vol = vol_menu.addAction("调节音量...")
        act_vol.triggered.connect(self._show_volume_slider)

        # 一键静音
        act_mute = menu.addAction("静音")
        act_mute.setCheckable(True)
        act_mute.setChecked(self.muted)
        act_mute.triggered.connect(self._toggle_mute)

        # 看屏间隔设置（可随意调整）
        watch_menu = menu.addMenu("看屏间隔")
        for sec in (10, 25, 60, 120, 300):
            act = watch_menu.addAction(f"{sec} 秒")
            act.setCheckable(True)
            act.setChecked(abs(self.watch_interval - sec) < 0.5)
            act.triggered.connect(lambda checked=False, s=sec: self._set_watch_interval(s))
        watch_menu.addSeparator()
        act_custom = watch_menu.addAction("自定义…")
        act_custom.triggered.connect(self._custom_watch_interval)

        # 看屏朗读开关
        act_watch = menu.addAction("看屏朗读")
        act_watch.setCheckable(True)
        act_watch.setChecked(self.watch_speech)
        act_watch.triggered.connect(self._toggle_watch_speech)

        menu.addSeparator()
        menu.addAction("退出", self.close)
        menu.exec(event.globalPos())

    def closeEvent(self, event):
        if hasattr(self, "bubble_win"):
            self.bubble_win.close()
        super().closeEvent(event)

    # ---- 功能 ----
    def _toggle_input(self):
        if self.input_visible:
            self.input_widget.hide()
            self.input_visible = False
        else:
            self.input_widget.show()
            self.input_visible = True
            self.entry.setFocus()
        self.adjustSize()
        self._sync_bubble()

    def _toggle_topmost(self):
        on = not (self.windowFlags() & Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.bubble_win.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()
        self.bubble_win.show()
        self._sync_bubble()

    def _switch_portrait(self):
        if len(self.portraits) <= 1:
            self.set_bubble("只有一张立绘哦~")
            return
        self.current_portrait_idx = (self.current_portrait_idx + 1) % len(self.portraits)
        self._apply_portrait()
        self.adjustSize()
        self._sync_bubble()

    def _open_history(self):
        if self.history_window is not None:
            self.history_window.close()
            self.history_window = None
        dlg = QDialog(self)
        dlg.setWindowTitle("艾雅法拉 - 历史对话")
        dlg.resize(460, 540)
        dlg.setWindowFlag(Qt.WindowStaysOnTopHint)
        lay = QVBoxLayout(dlg)
        text = QTextEdit(dlg)
        text.setReadOnly(True)
        text.setStyleSheet("font-size: 13px; border: none;")
        if not self.chat_log:
            text.setPlainText("（还没有对话记录哦~）")
        else:
            lines = ["【历史对话记录】", ""]
            for e in self.chat_log:
                lines.append(f"{e['who']}：")
                lines.append(e["text"])
                lines.append("")
            text.setPlainText("\n".join(lines))
        lay.addWidget(text)
        dlg.show()
        self.history_window = dlg

    def set_bubble(self, text):
        self.bubble.set_text(text)
        self.bubble_win.adjustSize()
        self._sync_bubble()

    def _append_chat(self, who, text):
        self.chat_log.append({"who": who, "text": text, "ts": time.time()})
        self._save_memory()

    def _save_memory(self):
        """持久化记忆：history 去掉 system 消息后保存，chat_log 全量保存。"""
        save_memory(
            [m for m in self.history if m["role"] != "system"],
            self.chat_log,
        )

    def _chat_messages(self):
        """把 history 转成发给 AI 的消息（去掉 ts，动态注入当前时间）。"""
        now = time.strftime("%Y年%m月%d日 %H:%M", time.localtime())
        weekday = ["一", "二", "三", "四", "五", "六", "日"][time.localtime().tm_wday]
        system = {
            "role": "system",
            "content": (
                self._build_persona()
                + f"\n\n【当前时间】现在是 {now}（星期{weekday}）。\n"
                "【硬性规则 - 每次回复都必须遵守】\n"
                "1. 必须根据【当前时间】判断问候：早上说「早上好」、中午说「中午好」、晚上说「晚上好」。\n"
                "2. 只有当现在是深夜（23:00 之后）且用户主动说要去睡觉时，才说「晚安」。\n"
                "3. 【任何情况下都禁止在回复末尾固定加「晚安」】——这是最重要的一条。\n"
                "4. 【禁止沿用对话历史里出现过的旧问候语】——无论历史里有没有「晚安」，"
                "都按当前时间重新判断，绝不重复旧词。\n"
                "5. 也就是说：哪怕你上一轮说了「晚安」，如果现在是第二天早上，你下一轮就必须改说「早上好」。"
            ),
        }
        msgs = [system]
        msgs += [
            {"role": m["role"], "content": m["content"]}
            for m in self.history if m["role"] != "system"
        ][-self.client.max_history:]
        return msgs

    # ---- 对话 ----
    def send(self):
        if not self.client.is_ready:
            self.set_bubble("前辈，我还没有配置好 AI 服务哦~")
            return
        text = self.entry.text().strip()
        if not text:
            return
        self.entry.clear()
        self.history.append({"role": "user", "content": text, "ts": time.time()})
        self._append_chat("前辈", text)
        self.set_bubble("（正在听……）")
        threading.Thread(target=self._reply, daemon=True).start()

    def _reply(self):
        try:
            resp = self._chat_with_search()
            self.history.append({"role": "assistant", "content": resp, "ts": time.time()})
            self.reply_ready.emit(resp)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _on_reply(self, resp):
        self._append_chat("艾雅法拉", resp)
        self.set_bubble(resp)
        # 语音朗读（后台合成，不阻塞界面）
        threading.Thread(target=self._speak_worker, args=(resp,), daemon=True).start()

    def _on_watch_reply(self, resp):
        """看屏评论：只显示气泡，是否朗读由「看屏朗读」开关决定。"""
        self._append_chat("艾雅法拉", resp)
        self.set_bubble(resp)
        if self.watch_speech:
            threading.Thread(target=self._speak_worker, args=(resp,), daemon=True).start()

    def _toggle_watch_speech(self):
        self.watch_speech = not self.watch_speech
        self.set_bubble("看屏时会说话啦~" if self.watch_speech else "看屏时安静不说话啦~")

    def _set_watch_interval(self, seconds):
        """设置看屏间隔（秒），立即生效并保存到配置。"""
        seconds = max(5, int(seconds))
        self.watch_interval = seconds
        if hasattr(self, "watch_timer"):
            self.watch_timer.stop()
            self.watch_timer.start(seconds * 1000)
        self._save_interval_to_config()
        self.set_bubble(f"（看屏间隔已设为 {seconds} 秒~）")

    def _custom_watch_interval(self):
        """弹输入框，允许任意设置间隔秒数。"""
        val, ok = QInputDialog.getInt(
            self, "看屏间隔", "输入自动看屏的间隔秒数（5~3600）：",
            self.watch_interval, 5, 3600, 5
        )
        if ok:
            self._set_watch_interval(val)

    def _save_interval_to_config(self):
        """把当前间隔写回 config，重启后仍生效。"""
        try:
            path = _p(self._config_name)
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg.setdefault("pet", {})["screenshot_interval_sec"] = self.watch_interval
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _show_error(self, msg):
        self.set_bubble(f"（出错了：{msg}）")

    def _warm_up(self):
        """预加载模型：发一个极短请求，让模型加载进显存。"""
        try:
            self.client.chat([{"role": "user", "content": "你好"}])
        except Exception:
            pass

    def _chat_with_search(self):
        resp = self.client.chat(self._chat_messages())
        if not self.search_enabled:
            return resp
        for _ in range(3):
            m = re.search(r"\[\[SEARCH:(.+?)\]\]", resp, re.S)
            if not m:
                break
            query = m.group(1).strip()
            self.bubble_update.emit(f"（我去查一下「{query}」……）")
            try:
                results = web_search(query, self.search_max)
                context = "[网络搜索结果] 关于「{}」：\n{}".format(query, format_results(results))
            except Exception as e:
                context = f"[网络搜索失败] {e}"
            self.history.append({"role": "assistant", "content": resp, "ts": time.time()})
            self.history.append({"role": "user", "content": context, "ts": time.time()})
            resp = self.client.chat(self._chat_messages())
        return resp

    # ---- 看屏 ----
    def take_screenshot_now(self):
        if not self.vision_enabled:
            self.set_bubble("这个版本没有视觉能力哦~")
            return
        self.set_bubble("（偷偷看前辈一眼……）")
        threading.Thread(target=self._watch_screen, daemon=True).start()

    def _auto_watch(self):
        if self.entry.hasFocus() or self.entry.text().strip():
            return
        self._watch_screen()

    def _watch_screen(self):
        if not self.vision_enabled:
            return
        if self._watching:
            return
        self._watching = True
        threading.Thread(target=self._watch_screen_worker, daemon=True).start()

    def _watch_screen_worker(self):
        try:
            img = ImageGrab.grab()
            max_side = 1280
            ratio = max_side / max(img.size)
            if ratio < 1:
                img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            prompt = (
                "你是艾雅法拉，正陪在前辈身边。下面这张是前辈此刻的电脑屏幕。"
                "请用你的口吻（称对方为前辈、句尾带~、语气软糯）"
                "简短地说一句你对所见内容的关心或评论，一两句话即可。\n"
                "【禁止】直接复制或延续屏幕上已有的旧问候词（如「晚安」）——根据当下语境说当下的话。"
            )
            resp = self.client.analyze_image(buf.getvalue(), prompt)
            self.watch_reply.emit(resp)
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._watching = False


def main():
    app = QApplication(sys.argv)
    config_name = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    pet = EyjaPet(config_name)
    pet.show()
    pet.bubble_win.show()
    QTimer.singleShot(0, pet._sync_bubble)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
