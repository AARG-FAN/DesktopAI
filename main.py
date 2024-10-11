# main.py
#autuor： AI研究室-帆哥
#2024.10.09
import webbrowser
from datetime import datetime
import sys
import platform
import subprocess
import os
import random
import json
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QDialog, QScrollArea, QLineEdit, QMessageBox, QFileDialog, QComboBox, QSpinBox,
    QSystemTrayIcon, QMenu, QAction, QSizePolicy, QStyle, QInputDialog, QGraphicsOpacityEffect
)
from PyQt5.QtGui import QPixmap, QIcon, QMovie, QTextCursor, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint, QEvent, QSize, QFileSystemWatcher, QTimer, QPropertyAnimation, QEasingCurve, pyqtSlot
from PIL import Image

# 导入重构后的VoiceAssistant
from main_program import VoiceAssistant

# 配置文件路径
CONFIG_FILE = "config.json"

def resource_path(relative_path):
    """ 获取资源文件的绝对路径，适用于打包后的可执行文件 """
    try:
        # PyInstaller 创建临时文件夹，并存储路径在 _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config():
    """ 加载配置文件 """
    if not os.path.exists(CONFIG_FILE):
        # 如果配置文件不存在，创建一个默认配置
        default_config = {
            "volcano_api_key": {
                "appid": "YOUR_VOLCANO_APPID",
                "access_token": "YOUR_VOLCANO_ACCESS_TOKEN"
            },
            "zhipuai_api_key": "YOUR_ZHIPUAI_API_KEY",
            "voice_tone": "lovey-dovey",
            "log_file_path": "log/conversation.log",
            "history_limit": 1000,
            "user": {
                "uid": "2101710118"
            },
            "voice_type": "BV700_V2_streaming",
            "roles": {
                "role1": {
                    "gif1": "assets/role1/gif1.gif",
                    "gif2": "assets/role1/gif2.gif"
                },
                "role2": {
                    "gif1": "assets/role2/gif1.gif",
                    "gif2": "assets/role2/gif2.gif"
                }
            },
            "selected_role": "role1",
            "wake_up_word": ""  
        }
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config
    else:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_config(config):
    """ 保存配置文件 """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

class ClickableLabel(QLabel):
    clicked = pyqtSignal()  # 定义一个信号

    def mousePressEvent(self, event):
        self.clicked.emit()  # 触发信号

class DescriptionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图片描述")
        self.setFixedSize(300, 150)  # 固定大小，防止窗口过大
        self.setStyleSheet("""
            QDialog {
                background-color: #2e2e2e;
                color: white;
                border: 1px solid #555;
                border-radius: 10px;
            }
            QLabel {
                font-size: 12px;  /* 减小字体大小 */
                color: white;     /* 确保文字为白色 */
            }
            QLineEdit {
                background-color: #3e3e3e;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #337ab7;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
        """)

        layout = QVBoxLayout()

        self.label = QLabel("请描述一下您想搜索的内容:")
        layout.addWidget(self.label)

        self.input = QLineEdit()
        layout.addWidget(self.input)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_description(self):
        return self.input.text().strip()


class KeyPressEater(QObject):
    """事件过滤器，用于捕捉按键事件"""

    def __init__(self, parent=None, skip_callback=None, communicator=None):
        super().__init__(parent)
        self.skip_callback = skip_callback
        self.communicator = communicator
        self.sleep_mode = False

        if self.communicator:
            self.communicator.sleep_mode_changed.connect(self.on_sleep_mode_changed)

    @pyqtSlot(bool)
    def on_sleep_mode_changed(self, sleep):
        self.sleep_mode = sleep

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            # 检查事件对象是否是 QLineEdit 或其子类
            if self.is_in_allowed_widget(obj):
                return False  # 允许事件通过

            else:
                # 处理空格键和回车键等
                if event.key() == Qt.Key_Space:
                    print("空格键被按下")  # 已有的调试信息
                    if self.skip_callback:
                        self.skip_callback()
                    return True  # 事件已处理
                elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                    print("回车键被按下")  # 添加新的调试信息
                    # 不做任何处理，确保回车键只触发发送消息
        return super().eventFilter(obj, event)

    def is_in_allowed_widget(self, obj):
        """检查事件是否发生在允许接收键盘事件的控件上"""
        allowed_classes = (QLineEdit,)
        current_obj = obj
        while current_obj:
            if isinstance(current_obj, allowed_classes):
                return True
            current_obj = current_obj.parent()
        return False

class ClickableImageLabel(QLabel):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path

    def mouseDoubleClickEvent(self, event):
        # 打开图像文件
        import subprocess
        import platform

        if platform.system() == 'Darwin':       # macOS
            subprocess.call(('open', self.image_path))
        elif platform.system() == 'Windows':    # Windows
            os.startfile(self.image_path)
        else:                                   # Linux variants
            subprocess.call(('xdg-open', self.image_path))


class Communicate(QObject):
    """ 自定义信号用于线程与UI通信 """
    ai_reply_signal = pyqtSignal(str)
    user_message_signal = pyqtSignal(str)
    ai_speaking_started = pyqtSignal()
    ai_speaking_finished = pyqtSignal()
    sleep_mode_changed = pyqtSignal(bool)  # 新增：睡眠模式变化信号
    wake_up_signal = pyqtSignal()    

class ChatDialog(QDialog):
    def __init__(self, parent=None, config=None, communicator=None, assistant=None):
        super().__init__(parent)
        self.setWindowTitle("AI桌面助手")
        self.setGeometry(100, 100, 500, 600)
        self.config = config
        self.communicator = communicator
        self.assistant = assistant
        self.init_ui()
        self.animation = None  # 添加这一行
        self.last_timestamp = datetime.now()
                # 设置定时器，每隔1分钟检查一次
        self.timestamp_timer = QTimer(self)
        self.timestamp_timer.timeout.connect(self.check_and_display_timestamp)
        self.timestamp_timer.start(60000)  # 每60,000毫秒（1分钟）检查一次

        # 第一次打开聊天窗口时显示时间戳
        self.display_timestamp()

        if self.communicator:
            # 连接 ai_reply_signal 到 display_ai_message
            self.communicator.ai_reply_signal.connect(self.display_ai_message)
            self.communicator.user_message_signal.connect(self.display_user_message)


    def check_and_display_timestamp(self):
        current_time = datetime.now()
        elapsed_minutes = (current_time - self.last_timestamp).total_seconds() / 60
        if elapsed_minutes >= 10:
            self.display_timestamp()
            self.last_timestamp = current_time

    def display_timestamp(self):
        current_time_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        timestamp_label = QLabel(current_time_str)
        timestamp_label.setAlignment(Qt.AlignCenter)
        timestamp_label.setStyleSheet("""
            QLabel {
                background-color: rgba(128, 128, 128, 0.5);  /* 半透明灰色背景 */
                color: white;
                border-radius: 5px;  /* 减小圆角半径 */
                padding: 2px 5px;    /* 减小内边距 */
                font-size: 8px;      /* 减小字体大小 */
                margin-top: 10px;
                margin-bottom: 10px;
            }
        """)
        self.chat_layout.addWidget(timestamp_label, alignment=Qt.AlignCenter)
        self.chat_layout.addSpacing(5)
        QTimer.singleShot(10, self.scroll_to_bottom)



    def closeEvent(self, event):
        """在聊天窗口关闭时断开信号连接"""
        if self.communicator:
            try:
                self.communicator.ai_reply_signal.disconnect(self.display_ai_message)
                self.communicator.user_message_signal.disconnect(self.display_user_message)
            except TypeError:
                # 如果信号未连接，忽略
                pass
        super().closeEvent(event)

    def display_ai_message(self, message):
        """显示AI的回复"""
        print("ChatDialog - AI 回复:", message)  # 调试信息

        if message.startswith("[IMAGE]"):
            image_path = message[len("[IMAGE]"):].strip()
            self.display_image_message("AI", image_path)
        else:
            self.display_message("AI", message)
            # 播放TTS语音
            if self.assistant:
                threading.Thread(
                    target=self.assistant.generate_and_play_tts,
                    args=(message, self.config.get("voice_tone", "lovey-dovey")),
                    daemon=True
                ).start()

    def display_user_message(self, message):
        """显示用户的消息"""
        self.display_message("您", message)  

    def scroll_to_bottom(self):
        """平滑滚动聊天区域到底部"""
        scrollbar = self.scroll_area.verticalScrollBar()
        
        # 停止任何正在进行的动画
        if self.animation and self.animation.state() == QPropertyAnimation.Running:
            self.animation.stop()
        
        # 获取当前值和目标值
        current_value = scrollbar.value()
        target_value = scrollbar.maximum()
        
        # 创建动画对象
        self.animation = QPropertyAnimation(scrollbar, b"value")
        self.animation.setDuration(300)  # 动画持续时间为300毫秒，可根据需要调整
        self.animation.setStartValue(current_value)
        self.animation.setEndValue(target_value)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # 动画结束时，确保滚动条到达最大值
        self.animation.finished.connect(lambda: scrollbar.setValue(target_value))
        
        # 启动动画
        self.animation.start()

    def init_ui(self):
        layout = QVBoxLayout()

        hints = [
            "小提示：按空格可以跳过当前语音",
            "小提示：你可以双击图片放大查看",
            "小提示：休眠后通过说出唤醒词以及点击唤醒让AI重新工作",
            "小提示：长时间不用可以右键选择休眠",
            "小提示：可以语音查询历史对话内容"
            # 可以添加更多提示
        ]

        # 随机选择一个提示
        hint_text = random.choice(hints)
        self.skip_label = QLabel(hint_text)
        self.skip_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.skip_label)

        # 设置淡出效果的函数
        def fade_out_label():
            # 创建透明度效果
            self.opacity_effect = QGraphicsOpacityEffect()
            self.skip_label.setGraphicsEffect(self.opacity_effect)

            # 创建动画
            self.animation = QPropertyAnimation(self.opacity_effect, b"opacity")
            self.animation.setDuration(1000)  # 动画持续时间为1秒
            self.animation.setStartValue(1)
            self.animation.setEndValue(0)
            self.animation.setEasingCurve(QEasingCurve.InOutQuad)
            self.animation.start()

            # 动画结束后，隐藏标签
            self.animation.finished.connect(self.skip_label.hide)

        # 在5秒后开始淡出动画
        QTimer.singleShot(5000, fade_out_label)


        # 对话显示区域使用一个垂直布局来容纳多个水平布局
        self.chat_display = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_display)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_display.setLayout(self.chat_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.chat_display)
        self.scroll_area.setStyleSheet("background-color: #2e2e2e;")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)


        layout.addWidget(self.scroll_area)
            # 输入框和上传按钮
        input_layout = QHBoxLayout()

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("输入您的消息...")
        self.user_input.setStyleSheet("""
            QLineEdit {
                background-color: #3e3e3e;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        font = QFont("Microsoft YaHei", 10, QFont.Bold)
        self.user_input.setFont(font)
        self.user_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.user_input)

        upload_button = QPushButton("上传图像")
        upload_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                padding: 5px 10px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        font = QFont("Microsoft YaHei", 10, QFont.Bold)
        upload_button.setFont(font)
        upload_button.clicked.connect(self.upload_image)
        upload_button.setFocusPolicy(Qt.NoFocus)  # 禁止上传按钮获得焦点
        input_layout.addWidget(upload_button)

        layout.addLayout(input_layout)

        # 发送按钮
        send_button = QPushButton("发送")
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
        """)
        send_button.clicked.connect(self.send_message)
        layout.addWidget(send_button)

        self.setLayout(layout)

    def send_message(self, emotion='NEUTRAL'):
        user_text = self.user_input.text().strip()
        if not user_text:
            return

        self.user_input.clear()

        # 启动后台线程处理用户输入
        if self.assistant:
            threading.Thread(
                target=self.assistant.process_user_input,
                args=(user_text, emotion, False), 
                daemon=True
            ).start()

        # 将焦点设置回输入框，防止回车键触发其他按钮
        self.user_input.setFocus()

    def upload_image(self):
        """上传图像并执行图片搜索技能"""
        # 打开文件对话框选择图像
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图像",
            "",
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.gif);;所有文件 (*)",
            options=options
        )
        if file_path:
            # 显示上传的图像路径
            self.display_image_message("您", file_path)
            # 使用自定义描述输入对话框
            description_dialog = DescriptionDialog(self)
            if description_dialog.exec_() == QDialog.Accepted:
                description = description_dialog.get_description()
                if description:
                    user_text = description
                else:
                    user_text = "请描述一下这张图里面的内容"  # 默认描述
            else:
                user_text = "请描述一下这张图里面的内容"  # 默认描述

            print(f"用户描述: {user_text}")  # 调试信息
            sys.stdout.flush()

            # 定义一个后台线程函数来执行图像搜索
            def run_image_search():
                result = self.assistant.execute_image_search(user_text, file_path)
                if result:
                    content = result.get('content', '')
                    if result.get('type') == 'text':
                        # 将AI的回复添加到对话历史和日志
                        self.assistant.messages.append({"role": "assistant", "content": content})
                        self.assistant.append_to_conversation_log({"role": "assistant", "content": content})
                        if len(self.assistant.messages) > self.assistant.MAX_LOG_ENTRIES:
                            self.assistant.messages.pop(0)
                        # 通过信号发送AI的回复到前端
                        self.communicator.ai_reply_signal.emit(content)
                    elif result.get('type') == 'image_path':
                        image_full_path = result.get('content', '')
                        msg = f"图像生成好啦，请查看"
                        # 将AI的回复添加到对话历史和日志
                        self.assistant.messages.append({"role": "assistant", "content": msg})
                        self.assistant.append_to_conversation_log({"role": "assistant", "content": msg})
                        if len(self.assistant.messages) > self.assistant.MAX_LOG_ENTRIES:
                            self.assistant.messages.pop(0)
                        # 通过信号发送AI的回复到前端
                        self.communicator.ai_reply_signal.emit(msg)
                        # 在聊天窗口中显示图像
                        self.display_image(image_full_path)
                    else:
                        error = result.get('content', '未知错误')
                        msg = f"执行技能时出错：{error}"
                        # 将错误信息添加到对话历史和日志
                        self.assistant.messages.append({"role": "assistant", "content": msg})
                        self.assistant.append_to_conversation_log({"role": "assistant", "content": msg})
                        if len(self.assistant.messages) > self.assistant.MAX_LOG_ENTRIES:
                            self.assistant.messages.pop(0)
                        # 通过信号发送错误信息到前端
                        self.communicator.ai_reply_signal.emit(msg)

            # 启动后台线程
            threading.Thread(
                target=run_image_search,
                daemon=True
            ).start()

    def display_message(self, sender, message):
        # 检查是否需要显示新的时间戳
        current_time = datetime.now()
        elapsed_minutes = (current_time - self.last_timestamp).total_seconds() / 60
        if elapsed_minutes >= 10:
            self.display_timestamp()
            self.last_timestamp = current_time

        if sender == "AI":
            alignment = Qt.AlignLeft
            color = "#d1ffd6"  # AI消息背景色
            avatar_path = resource_path("assets/thumbnail/ai.png")
            display_name = "AI"
        else:
            alignment = Qt.AlignRight
            color = "#ffffff"  # 用户消息背景色
            avatar_path = resource_path("assets/thumbnail/user.png")
            display_name = "我"

        # 加载头像
        avatar_label = QLabel()
        avatar_pixmap = QPixmap(avatar_path)
        avatar_pixmap = avatar_pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        avatar_label.setPixmap(avatar_pixmap)
        avatar_label.setFixedSize(30, 30)
        avatar_label.setStyleSheet("border-radius: 15px;")  # 使头像为圆形

        # 显示名字
        name_label = QLabel(display_name)
        name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;  /* 设置用户名文字为白色 */
                font-size: 12px;
                margin-left: 5px;
                margin-right: 5px;
            }
        """)

        # 创建一个水平布局来容纳头像和用户名
        avatar_name_layout = QHBoxLayout()
        avatar_name_layout.setSpacing(5)  # 设置头像和用户名之间的间距
        if sender == "AI":
            avatar_name_layout.addWidget(avatar_label)
            avatar_name_layout.addWidget(name_label)
            avatar_name_layout.addStretch()
            avatar_name_layout.setAlignment(Qt.AlignLeft)
        else:
            avatar_name_layout.addStretch()
            avatar_name_layout.addWidget(name_label)
            avatar_name_layout.addWidget(avatar_label)
            avatar_name_layout.setAlignment(Qt.AlignRight)

        # 创建消息框
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        font = QFont("Microsoft YaHei", 10)
        message_label.setFont(font)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        message_label.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: #000000;  /* 设置消息文字为黑色 */
                border: 1px solid #ccc;
                border-radius: 15px;
                padding: 10px;
                max-width: 300px;

            }}
        """)
        message_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        # 将消息内容添加到消息布局
        message_container_layout = QVBoxLayout()
        message_container_layout.addLayout(avatar_name_layout)
        message_container_layout.addWidget(message_label)

        # 使用 alignment 来调整整个消息布局的位置
        message_wrapper = QHBoxLayout()
        if sender == "AI":
            message_wrapper.addLayout(message_container_layout)
            message_wrapper.addStretch()  # 让AI的消息靠左显示
        else:
            message_wrapper.addStretch()  # 让用户的消息靠右显示
            message_wrapper.addLayout(message_container_layout)

        # 将消息布局添加到主聊天布局
        self.chat_layout.addLayout(message_wrapper)
        self.chat_layout.addSpacing(10)

        # 自动滚动到底部
        QTimer.singleShot(10, self.scroll_to_bottom)


    def display_image_message(self, sender, image_path):
        # 检查是否需要显示新的时间戳
        current_time = datetime.now()
        elapsed_minutes = (current_time - self.last_timestamp).total_seconds() / 60
        if elapsed_minutes >= 10:
            self.display_timestamp()
            self.last_timestamp = current_time

        if sender == "AI":
            alignment = Qt.AlignLeft
            color = "#d1ffd6"  # AI消息背景色
            avatar_path = resource_path("assets/thumbnail/ai.png")
            display_name = "AI"
        else:
            alignment = Qt.AlignRight
            color = "#ffffff"  # 用户消息背景色
            avatar_path = resource_path("assets/thumbnail/user.png")
            display_name = "我"

        # 加载头像
        avatar_label = QLabel()
        avatar_pixmap = QPixmap(avatar_path)
        avatar_pixmap = avatar_pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        avatar_label.setPixmap(avatar_pixmap)
        avatar_label.setFixedSize(30, 30)
        avatar_label.setStyleSheet("border-radius: 15px;")  # 使头像为圆形

        # 显示名字
        name_label = QLabel(display_name)
        name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;  /* 设置用户名文字为白色 */
                font-size: 12px;
                margin-left: 5px;
                margin-right: 5px;
            }
        """)

        # 使用 ClickableImageLabel 显示图像
        image_label = ClickableImageLabel(image_path)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            image_label.setText("无法加载图像。")
        else:
            pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(pixmap)
        image_label.setStyleSheet("padding: 5px;")

        # 创建一个水平布局来容纳头像和用户名
        avatar_name_layout = QHBoxLayout()
        avatar_name_layout.setSpacing(5)
        if sender == "AI":
            avatar_name_layout.addWidget(avatar_label)
            avatar_name_layout.addWidget(name_label)
            avatar_name_layout.addStretch()
            avatar_name_layout.setAlignment(Qt.AlignLeft)
        else:
            avatar_name_layout.addStretch()
            avatar_name_layout.addWidget(name_label)
            avatar_name_layout.addWidget(avatar_label)
            avatar_name_layout.setAlignment(Qt.AlignRight)

        # 将图像内容添加到消息布局
        message_container_layout = QVBoxLayout()
        message_container_layout.addLayout(avatar_name_layout)
        message_container_layout.addWidget(image_label)

        # 使用 alignment 来调整图像消息的位置
        message_wrapper = QHBoxLayout()
        if sender == "AI":
            message_wrapper.addLayout(message_container_layout)
            message_wrapper.addStretch()  # 让AI的消息靠左显示
        else:
            message_wrapper.addStretch()  # 让用户的消息靠右显示
            message_wrapper.addLayout(message_container_layout)

        # 将消息布局添加到主聊天布局
        self.chat_layout.addLayout(message_wrapper)
        self.chat_layout.addSpacing(10)

        # 自动滚动到底部
        QTimer.singleShot(10, self.scroll_to_bottom)



class SettingsDialog(QDialog):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setGeometry(150, 150, 400, 400)
        self.config = config
        self.init_ui()
        

    def init_ui(self):
        layout = QVBoxLayout()

        # 用户 UID 设置
        uid_layout = QHBoxLayout()
        uid_label = QLabel("用户 UID:")
        self.uid_input = QLineEdit()
        self.uid_input.setText(self.config.get("user", {}).get("uid", "2101710118"))
        uid_layout.addWidget(uid_label)
        uid_layout.addWidget(self.uid_input)
        layout.addLayout(uid_layout)

        # Voice Type 设置
        voice_type_layout = QHBoxLayout()
        voice_type_label = QLabel("Voice Type:")
        self.voice_type_input = QLineEdit()
        self.voice_type_input.setText(self.config.get("voice_type", "BV700_V2_streaming"))
        voice_type_layout.addWidget(voice_type_label)
        voice_type_layout.addWidget(self.voice_type_input)
        layout.addLayout(voice_type_layout)

        # 火山 API Key - AppID
        volcano_layout = QHBoxLayout()
        volcano_label = QLabel("火山 AppID:")
        self.volcano_appid_input = QLineEdit()
        self.volcano_appid_input.setText(self.config.get("volcano_api_key", {}).get("appid", ""))
        volcano_layout.addWidget(volcano_label)
        volcano_layout.addWidget(self.volcano_appid_input)
        layout.addLayout(volcano_layout)

        # 火山 API Key - Access Token
        volcano_token_layout = QHBoxLayout()
        volcano_token_label = QLabel("火山 Access Token:")
        self.volcano_token_input = QLineEdit()
        self.volcano_token_input.setText(self.config.get("volcano_api_key", {}).get("access_token", ""))
        volcano_token_layout.addWidget(volcano_token_label)
        volcano_token_layout.addWidget(self.volcano_token_input)
        layout.addLayout(volcano_token_layout)

        # 智谱 API Key
        zhipuai_layout = QHBoxLayout()
        zhipuai_label = QLabel("智谱 API Key:")
        self.zhipuai_input = QLineEdit()
        self.zhipuai_input.setText(self.config.get("zhipuai_api_key", ""))
        zhipuai_layout.addWidget(zhipuai_label)
        zhipuai_layout.addWidget(self.zhipuai_input)
        layout.addLayout(zhipuai_layout)

        # 音色选择
        voice_layout = QHBoxLayout()
        voice_label = QLabel("音色选择:")
        self.voice_combo = QComboBox()
        self.voice_combo.addItems(["lovey-dovey", "happy", "sad", "angry"])
        current_voice = self.config.get("voice_tone", "lovey-dovey")
        index = self.voice_combo.findText(current_voice)
        if index != -1:
            self.voice_combo.setCurrentIndex(index)
        voice_layout.addWidget(voice_label)
        voice_layout.addWidget(self.voice_combo)
        layout.addLayout(voice_layout)

        # 上传日志文档
        log_layout = QHBoxLayout()
        log_label = QLabel("上传日志文档:")
        self.log_input = QLineEdit()
        self.log_input.setText(self.config.get("log_file_path", ""))
        log_button = QPushButton("浏览")
        log_button.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                border: none;
                padding: 5px 10px;
                font-size: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #31b0d5;
            }
        """)
        log_button.clicked.connect(self.browse_log_file)
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_input)
        log_layout.addWidget(log_button)
        layout.addLayout(log_layout)

        # 历史记录支持词条数
        history_layout = QHBoxLayout()
        history_label = QLabel("历史记录支持词条数:")
        self.history_spin = QSpinBox()
        self.history_spin.setRange(1, 10000)
        self.history_spin.setValue(self.config.get("history_limit", 1000))
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.history_spin)
        layout.addLayout(history_layout)

        # 保存按钮
        save_button = QPushButton("保存")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ec971f;
            }
        """)
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def browse_log_file(self):
        """浏览并选择日志文件"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择日志文档",
            "",
            "文档文件 (*.txt *.log);;所有文件 (*)",
            options=options
        )
        if file_path:
            self.log_input.setText(file_path)

    def save_settings(self):
        """保存设置到配置文件"""
        # 更新配置
        self.config["volcano_api_key"] = {
            "appid": self.volcano_appid_input.text().strip(),
            "access_token": self.volcano_token_input.text().strip()
        }
        self.config["zhipuai_api_key"] = self.zhipuai_input.text().strip()
        self.config["voice_tone"] = self.voice_combo.currentText()
        self.config["log_file_path"] = self.log_input.text().strip()
        self.config["history_limit"] = self.history_spin.value()
        # 保存新增的参数
        self.config["user"] = {
            "uid": self.uid_input.text().strip()
        }
        self.config["voice_type"] = self.voice_type_input.text().strip()
        # 保存到配置文件
        save_config(self.config)
        QMessageBox.information(self, "设置", "设置已保存！")
        self.close()

class TrayMenu(QMenu):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.init_menu()

    def init_menu(self):
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.main_window.show)
        self.addAction(show_action)

        hide_action = QAction("隐藏", self)
        hide_action.triggered.connect(self.main_window.hide)
        self.addAction(hide_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.main_window.open_settings_dialog)
        self.addAction(settings_action)

        # 新增：模式管理子菜单
        mode_menu = self.addMenu("模式管理")

        sleep_action = QAction("睡眠", self)
        sleep_action.triggered.connect(self.main_window.sleep_mode)
        mode_menu.addAction(sleep_action)

        wake_menu = mode_menu.addMenu("唤醒")

        direct_wake_action = QAction("直接唤醒", self)
        direct_wake_action.triggered.connect(self.main_window.wake_mode)
        wake_menu.addAction(direct_wake_action)

        set_wake_word_action = QAction("设置唤醒词", self)
        set_wake_word_action.triggered.connect(self.main_window.set_wake_up_word)
        wake_menu.addAction(set_wake_word_action)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(sys.exit)
        self.addAction(exit_action)

class DraggableLabel(QLabel):
    def __init__(self, parent=None, left_click_callback=None, right_click_callback=None):
        super().__init__(parent)
        self.parent_window = parent
        self.left_click_callback = left_click_callback
        self.right_click_callback = right_click_callback
        self._is_dragging = False
        self._drag_position = QPoint()
        self._click_threshold = 5  # 最小移动距离以区分点击和拖动
        self._mouse_press_pos = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
            self._mouse_press_pos = event.pos()
            self._drag_position = event.globalPos() - self.parent_window.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            # 调用右键点击回调，并传递全局位置
            if self.right_click_callback:
                self.right_click_callback(event.globalPos())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            move_distance = (event.pos() - self._mouse_press_pos).manhattanLength()
            if move_distance > self._click_threshold:
                self._is_dragging = True
                self.parent_window.move(event.globalPos() - self._drag_position)
                event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._is_dragging:
                # 触发左键点击回调
                if self.left_click_callback:
                    self.left_click_callback()
            self._is_dragging = False
            event.accept()
        elif event.button() == Qt.RightButton:
            # 右键事件已在 mousePressEvent 中处理
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class MainWindow(QWidget):
    def __init__(self, config, communicator, assistant):
        super().__init__()
        self.config = config
        self.communicator = communicator
        self.assistant = assistant
        self.chat_dialog = None
        self.chat_is_open = False  # 初始化标志
        self.selected_role = self.config.get("selected_role", "role1")
        self.load_role_gifs()

        # 初始化拖动相关变量
        self._is_dragging = False
        self._drag_position = QPoint()
        self._mouse_press_pos = QPoint()

        self.init_ui()
        self.init_tray()
        self.init_key_event_filter()

        # 设置窗口为无边框、始终位于最前、工具窗口（不显示在任务栏）
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        # 可选：设置透明背景
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # 强制窗口获得焦点
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        # 连接 AI 回复信号到新的槽函数
        if self.communicator:
            self.communicator.ai_reply_signal.connect(self.handle_ai_reply)
            self.communicator.ai_speaking_started.connect(self.on_ai_speaking_started)
            self.communicator.ai_speaking_finished.connect(self.on_ai_speaking_finished)
            self.communicator.wake_up_signal.connect(self.wake_mode) 

    # 新增：睡眠模式
    def sleep_mode(self):
        """进入睡眠模式"""
        if self.communicator:
            self.communicator.sleep_mode_changed.emit(True)  # 通知进入睡眠模式
        QMessageBox.information(self, "睡眠模式", "AI已进入睡眠模式。")

    # 新增：唤醒模式
    def wake_mode(self):
        """退出睡眠模式并唤醒AI"""
        if self.communicator:
            self.communicator.sleep_mode_changed.emit(False)  # 通知退出睡眠模式
        QMessageBox.information(self, "唤醒", "AI已被唤醒。")

    # 新增：设置唤醒词
    def set_wake_up_word(self):
        """设置自定义唤醒词"""
        word, ok = QInputDialog.getText(self, "设置唤醒词", "请输入唤醒词:")
        if ok and word.strip():
            # 更新配置
            self.config['wake_up_word'] = word.strip()
            save_config(self.config)
            QMessageBox.information(self, "设置唤醒词", f"唤醒词已设置为: {word.strip()}")            

    def load_role_gifs(self):
        roles = self.config.get("roles", {})
        selected_role = self.selected_role
        if selected_role in roles:
            role_gifs = roles[selected_role]
            self.gif1_path = resource_path(role_gifs.get("gif1"))
            self.gif2_path = resource_path(role_gifs.get("gif2"))
        else:
            QMessageBox.critical(self, "错误", f"未找到角色 '{selected_role}' 的 GIF 配置。")
            sys.exit(1)

    def switch_gif(self, gif_path):
        """切换显示的 GIF"""
        if gif_path and os.path.exists(gif_path):
            #print(f"切换到 GIF: {gif_path}")  # 调试信息
            self.movie.stop()
            new_movie = QMovie(gif_path)
            if not new_movie.isValid():
                print(f"无法加载 GIF: {gif_path}")
                return
            new_movie.setScaledSize(QSize(200, 200))  # 使用固定的缩放尺寸
            self.pet_label.setMovie(new_movie)
            new_movie.start()
            self.movie = new_movie  # 更新引用
        else:
            QMessageBox.critical(self, "错误", f"GIF 文件 '{gif_path}' 未找到。")
            sys.exit(1)

    def on_ai_speaking_started(self):
        """当AI开始说话时切换为当前角色的 gif2"""
        gif_path = self.gif2_path  # 使用根据角色加载的 gif2 路径
        self.switch_gif(gif_path)

    def on_ai_speaking_finished(self):
        """当AI结束说话时切换为当前角色的 gif1"""
        gif_path = self.gif1_path  # 使用根据角色加载的 gif1 路径
        self.switch_gif(gif_path)


    # 添加鼠标事件处理函数
    def pet_label_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_press_pos = event.globalPos()
            self._is_dragging = False
            event.accept()
        elif event.button() == Qt.RightButton:
            self.show_custom_menu(event.globalPos())
            event.accept()

    def pet_label_mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            distance = (event.globalPos() - self._mouse_press_pos).manhattanLength()
            if distance > QApplication.startDragDistance():
                self._is_dragging = True
                self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            if self._is_dragging:
                self.move(event.globalPos() - self._drag_position)
                event.accept()
        else:
            event.ignore()

    def pet_label_mouseReleaseEvent(self, event):
        if not self._is_dragging:
            # 如果不是拖动，则认为是点击，打开聊天窗口
            self.open_chat_dialog()
        self._is_dragging = False
        event.accept() 

    def handle_ai_reply(self, message):
        """处理 AI 回复并播放 TTS"""
        print("MainWindow - AI 回复:", message)  # 调试信息
        # 仅当聊天窗口未打开时播放 TTS
        if not self.chat_is_open and self.assistant:
            threading.Thread(
                target=self.assistant.generate_and_play_tts,
                args=(message, self.config.get("voice_tone", "lovey-dovey")),
                daemon=True
            ).start()
        # 显示系统通知
        self.show_tray_message("AI 回复", message)

    def show_tray_message(self, title, message):
        """在系统托盘显示通知消息"""
        self.tray_icon.showMessage(
            title,
            message,
            QSystemTrayIcon.Information,
            3000  # 显示时间（毫秒）
        )

    def open_chat_dialog(self):
        """打开对话窗口，确保只有一个实例"""
        if self.chat_dialog is None or not self.chat_dialog.isVisible():
            self.chat_dialog = ChatDialog(self, self.config, self.communicator, self.assistant)
            self.chat_dialog.show()
            self.chat_is_open = True  # 设置标志为 True

            # 连接聊天窗口的关闭信号，以重置标志
            self.chat_dialog.finished.connect(self.on_chat_dialog_closed)
        else:
            self.chat_dialog.raise_()
            self.chat_dialog.activateWindow()

    def on_chat_dialog_closed(self):
        """聊天窗口关闭时调用，重置标志"""
        self.chat_is_open = False
    def init_key_event_filter(self):
        """初始化按键事件过滤器"""

        pass

    def init_ui(self):
        layout = QVBoxLayout()

        # 加载 GIF 动画
        try:
            gif_path = self.gif1_path  # 使用根据角色选择的 GIF 路径
            print(f"尝试加载 GIF 文件路径: {gif_path}")  # 调试信息
            if not os.path.exists(gif_path):
                raise FileNotFoundError(f"GIF 文件 '{gif_path}' 未找到。")
            self.movie = QMovie(gif_path)

            if not self.movie.isValid():
                raise ValueError(f"无法加载 GIF 文件: {gif_path}")

            # 设置固定的缩放尺寸，例如 200x200
            self.movie.setScaledSize(QSize(200, 200))

            # 使用 DraggableLabel 替换 QLabel
            self.pet_label = DraggableLabel(
                parent=self,
                left_click_callback=self.open_chat_dialog,  # 左键点击回调
                right_click_callback=self.show_custom_menu  # 右键点击回调
            )
            self.pet_label.setMovie(self.movie)
            self.pet_label.setFixedSize(200, 200)  # 确保 QLabel 有足够的空间显示动画
            self.pet_label.setAlignment(Qt.AlignCenter)
            self.pet_label.setStyleSheet("background-color: rgba(0, 0, 0, 0);")
            self.pet_label.setAttribute(Qt.WA_TranslucentBackground, True)
            self.movie.start()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载动画: {e}")
            sys.exit(1)

        layout.addWidget(self.pet_label)

        # 添加设置按钮
        settings_button = QPushButton("⚙")  # 使用齿轮图标或文字
        settings_button.setFixedSize(30, 30)
        settings_button.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: white;
                border: none;
                border-radius: 15px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #555555;
            }
        """)


        
        settings_button.clicked.connect(self.open_settings_dialog)
        # 将设置按钮放在主窗口的右上角
        settings_button.setParent(self)
        settings_button.move(self.width() - settings_button.width() - 10, 10)
        settings_button.raise_()

        self.setLayout(layout)

        # 确保窗口可以接收按键事件
        self.setFocusPolicy(Qt.StrongFocus)

    def handle_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.open_chat_dialog()
        elif event.button() == Qt.RightButton:
            self.show_custom_menu(event.globalPos())

    def show_custom_menu(self, position):
        """显示自定义右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2e2e2e;
                border: 1px solid #555;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QMenu::item {
                padding: 5px 30px 5px 30px;
                margin: 5px;
            }
            QMenu::item:selected {
                background-color: #3e3e3e;
            }
        """)

        # 添加“更换角色”菜单项
        change_role_action = menu.addAction("更换角色")
        # 添加“设置”菜单项
        settings_action = menu.addAction("设置")
        # 创建“模式管理”子菜单
        mode_menu = menu.addMenu("模式管理")
        
        # 在“模式管理”子菜单中添加“睡眠”和“唤醒”选项
        sleep_action = QAction("睡眠", self)
        sleep_action.triggered.connect(self.sleep_mode)
        mode_menu.addAction(sleep_action)
        
        wake_menu = mode_menu.addMenu("唤醒")
        
        # 在“唤醒”子菜单中添加“直接唤醒”和“设置唤醒词”选项
        direct_wake_action = QAction("直接唤醒", self)
        direct_wake_action.triggered.connect(self.wake_mode)
        wake_menu.addAction(direct_wake_action)
        
        set_wake_word_action = QAction("设置唤醒词", self)
        set_wake_word_action.triggered.connect(self.set_wake_up_word)
        wake_menu.addAction(set_wake_word_action)
        # 添加“关注我们”菜单项
        follow_us_action = menu.addAction("关注AI研究室")
        # 添加“关闭”菜单项
        close_action = menu.addAction("关闭程序")

        action = menu.exec_(position)
        if action == change_role_action:
            self.select_role_dialog()
        elif action == settings_action:
            self.open_settings_dialog()
        elif action == follow_us_action:
            self.open_follow_us()
        elif action == close_action:
            self.close_application()

    def open_follow_us(self):
        """打开关注我们的网址"""
        url = "https://space.bilibili.com/2161614"  # 请将此处的URL替换为您的目标网址
        try:
            webbrowser.open(url)
            print(f"已打开网页: {url}")  # 可选的调试信息
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开网页: {e}")

    def close_application(self):
        """关闭整个应用程序"""
        reply = QMessageBox.question(
            self,
            '确认退出',
            "您确定要退出应用程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            QApplication.instance().quit()            

    def update_config(self, new_config):
        self.config = new_config
        self.selected_role = self.config.get("selected_role", "role1")
        self.load_role_gifs()
        self.switch_gif(self.gif1_path)

    def select_role_dialog(self):
        """选择角色的对话框"""
        roles = list(self.config.get("roles", {}).keys())
        role, ok = QInputDialog.getItem(self, "选择角色", "请选择一个角色:", roles, 0, False)
        if ok and role:
            QMessageBox.information(self, "角色选择", f"您选择的角色是: {role}")
            self.selected_role = role
            self.config["selected_role"] = role

            # 获取所选角色的音色类型
            voice_type = self.config["roles"].get(role, {}).get("voice_type", "默认音色")
            self.config["voice_type"] = voice_type  # 更新音色类型

            save_config(self.config)
            self.load_role_gifs()
            self.switch_gif(self.gif1_path)


    def open_settings_dialog(self):
        """打开设置窗口"""
        self.settings_dialog = SettingsDialog(self, self.config)
        self.settings_dialog.show()

    def init_tray(self):
        """初始化系统托盘图标和菜单"""
        self.tray_icon = QSystemTrayIcon(self)
        icon_path = resource_path("assets/tray_icon.png")  # 替换为您的托盘图标路径
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_menu = TrayMenu(parent=self, main_window=self)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        """重写关闭事件，最小化到系统托盘"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "桌面小助理",
            "应用已最小化到系统托盘。",
            QSystemTrayIcon.Information,
            2000
        )

class DesktopAssistantApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.setQuitOnLastWindowClosed(False)
        self.config = load_config()
        self.communicator = Communicate()
        font = QFont("Microsoft YaHei", 10, QFont.Bold)
        self.setFont(font)        
        # 初始化VoiceAssistant
        self.assistant = VoiceAssistant(
            config_path="config.json",
            user_callback=self.communicator.user_message_signal.emit,  # 用户消息回调
            ai_callback=self.communicator.ai_reply_signal.emit,
            communicator=self.communicator  # 传递 communicator       # AI 回复回调
        )
        self.assistant.start()
        self.main_window = MainWindow(self.config, self.communicator, self.assistant)
        self.main_window.show()

        # 安装事件过滤器到 QApplication
        self.key_press_eater = KeyPressEater(
            skip_callback=self.assistant.skip_tts,
            communicator=self.communicator
        )
        self.installEventFilter(self.key_press_eater)
        # 新增：设置配置文件监控
        self.setup_config_watcher()

        # 连接唤醒信号到唤醒方法
        #self.communicator.wake_up_signal.connect(self.main_window.wake_mode)

    def setup_config_watcher(self):
        self.config_watcher = QFileSystemWatcher()
        self.config_watcher.addPath(CONFIG_FILE)
        self.config_watcher.fileChanged.connect(self.on_config_changed)

    def on_config_changed(self, path):
        print(f"配置文件 {path} 已更改，重新加载配置。")
        self.config = load_config()
        self.assistant.update_config(self.config)
        self.main_window.update_config(self.config)

def main():
    app = DesktopAssistantApp(sys.argv)
    # 指定编码为 utf-8 来读取样式表
    with open("styles.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
