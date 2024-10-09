# main_program.py
#autuor： AI研究室-帆哥
#2024.10.09
import textwrap  
import base64
import json
import os
import sys
import threading
import time
import uuid
import subprocess
from PIL import Image
from pydub import AudioSegment
import simpleaudio as sa
import pyaudio
import wave
import webrtcvad
import numpy as np
import re
import requests
from funasr import AutoModel
from zhipuai import ZhipuAI

class VoiceAssistant:
    def __init__(self, config_path="config.json", user_callback=None, ai_callback=None, communicator=None):
        """
        初始化VoiceAssistant类。

        :param config_path: 配置文件路径
        :param user_callback: 回调函数，用于将用户的消息传递给前端
        :param ai_callback: 回调函数，用于将AI的回复传递给前端
        """
        self.config = self.load_config(config_path)
        self.communicator = communicator
        self.user_callback = user_callback  # Callback function for user messages
        self.ai_callback = ai_callback      # Callback function for AI replies
        # Initialize API client
        self.client = ZhipuAI(api_key=self.config["zhipuai_api_key"])
        self.LOG_FILE_PATH = self.config.get("log_file_path", "log/conversation.log")
        self.MAX_LOG_ENTRIES = self.config.get("history_limit", 1000)
        self.appidcon = self.config["volcano_api_key"]["appid"]
        self.tokencon = self.config["volcano_api_key"]["access_token"]
        self.user_uid = self.config.get("user", {}).get("uid", "2101710118")
        self.voice_type = self.config.get("voice_type", "BV700_V2_streaming")
        # Emotion mapping
        self.emotion_mapping = {
            'NEUTRAL': 'lovey-dovey',
            'HAPPY': 'happy',
            'SAD': 'sad',
            'ANGRY': 'angry'
        }

        # Skills
        self.skills = {
            "web_search": "文字搜索",
            "image_search": "图片搜索",
            "code_interpreter": "代码解释器",
            "drawing": "画图",
            "log_talking": "历史纪录回答"
        }
        self.skill_names = list(self.skills.keys())

        # Locks and events
        self.skip_event = threading.Event()
        self.ai_speaking_lock = threading.Lock()
        self.input_lock = threading.Lock()

        # Initialize conversation log
        self.messages = self.load_conversation_log()

        # Initialize FunASR model
        self.model_dir = "iic/SenseVoiceSmall"
        self.model = AutoModel(
            model=self.model_dir,
            trust_remote_code=True,
            remote_code="./model.py",
            vad_model="fsmn-vad",
            vad_kwargs={"max_single_segment_time": 30000},
            device="cuda:0",
        )

        # Audio parameters
        self.RATE = 16000
        self.CHANNELS = 1
        self.FORMAT = pyaudio.paInt16
        self.FRAME_DURATION = 20  # ms
        self.FRAME_SIZE = int(self.RATE * (self.FRAME_DURATION / 1000))
        self.WAVE_OUTPUT_FILENAME = "output.wav"
        self.VAD_AGGRESSIVENESS = 3
        self.NUM_SILENT_FRAMES_THRESHOLD = int(800 / self.FRAME_DURATION)
        self.NUM_SILENT_FRAMES_THRESHOLD2 = int(2000 / self.FRAME_DURATION)

        # Initialize is_AI_speaking
        self.is_AI_speaking = False  # 初始化为False

    def skip_tts(self):
        """跳过当前的TTS播放"""
        self.skip_event.set()
    def update_config(self, new_config):
        self.config = new_config
        self.appidcon = self.config["volcano_api_key"]["appid"]
        self.tokencon = self.config["volcano_api_key"]["access_token"]
        self.user_uid = self.config.get("user", {}).get("uid", "2101710118")
        self.voice_type = self.config.get("voice_type", "BV700_V2_streaming")
        self.LOG_FILE_PATH = self.config.get("log_file_path", "log/conversation.log")
        self.MAX_LOG_ENTRIES = self.config.get("history_limit", 1000)

    def load_config(self, config_path):
        """加载配置文件"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件 '{config_path}' 未找到。")
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_conversation_log(self):
        """加载对话日志"""
        messages = []
        if not os.path.exists(self.LOG_FILE_PATH):
            return messages
        with open(self.LOG_FILE_PATH, "r", encoding="utf-8") as log_file:
            lines = log_file.readlines()
            lines = lines[-self.MAX_LOG_ENTRIES*2:]
            for line in lines:
                line = line.strip()
                if line.startswith("question:"):
                    content = line[len("question:"):].strip()
                    messages.append({"role": "user", "content": content})
                elif line.startswith("answer:"):
                    content = line[len("answer:"):].strip()
                    messages.append({"role": "assistant", "content": content})
        return messages

    def append_to_conversation_log(self, message):
        """将消息追加到对话日志"""
        if not isinstance(message, dict):
            print("append_to_conversation_log: message 不是字典类型，跳过记录。")
            return
        if "role" not in message or "content" not in message:
            print("append_to_conversation_log: message 缺少 'role' 或 'content' 键，跳过记录。")
            return

        with open(self.LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
            if message["role"] == "user":
                log_file.write(f"question: {message['content']}\n")
            elif message["role"] == "assistant":
                log_file.write(f"answer: {message['content']}\n")

        # 保持日志条目不超过最大限制
        with open(self.LOG_FILE_PATH, "r", encoding="utf-8") as log_file:
            lines = log_file.readlines()

        if len(lines) > self.MAX_LOG_ENTRIES * 2:
            lines = lines[-self.MAX_LOG_ENTRIES * 2:]
            with open(self.LOG_FILE_PATH, "w", encoding="utf-8") as log_file:
                log_file.writelines(lines)

    def detect_action_with_large_model(self, user_input):

        max_history = 20
        recent_messages = self.messages[-max_history:]
        
        # 格式化对话历史
        conversation_history = ""
        for msg in recent_messages:
            role = "用户" if msg["role"] == "user" else "AI"
            conversation_history += f"{role}: {msg['content']}\n"
        
        # 定义技能名称字符串
        skill_names_str = ', '.join(self.skill_names)
        """使用大模型检测用户请求需要的技能"""
        skill_names_str = ', '.join(self.skill_names)

        prompt = f"""
{conversation_history}
您是一个智能助理小帆，具有以下技能：{skill_names_str}。
每个技能的描述如下：
- **web_search（网页搜索）**：通过互联网搜索信息，回答用户的问题或提供最新的资讯。
- **image_search（桌面截图搜索）**：用户需要上传图片，或者让你看图片是什么并描述里面的具体内容，就截取当前电脑屏幕的截图，并根据用户的要求进行分析或查找相关信息。
- **drawing（画图，生成一张图）**：根据用户的描述，画一张画，或者生成一张对应的图像。
- **code_interpreter（生成图表）**：根据数据或描述，生成相应的图表，例如折线图、柱状图等。
- **log_talking（历史记录回答）**：之前你们聊过的话题会存档，根据历史纪录文档，或是之前聊过的内容来回答问题。
**任务：**

请按照以下步骤处理用户的请求：

1. **判断请求类型**：首先判断用户的请求是正常对话还是需要执行技能的任务。
   - 如果是正常对话，请直接回复用户，不使用任何技能。
   - 如果需要执行技能，请继续以下步骤。

2. **总结用户的请求**：用一句话总结用户的主要需求。

3. **分析需要使用的技能**：根据总结，判断需要使用哪些技能来完成用户的请求。

4. **为每个技能生成准确的输入**：根据技能的输入要求，为每个技能提供具体、详细的输入，确保技能能够正确执行。

5. **输出结果**：
   - 如果需要执行技能，按照指定的 JSON 格式返回技能序列和最终回复。
   - 如果是正常对话，直接给出对用户的回复，不要包含任何额外的文本或说明。

**请注意：**

- 只能使用提供的技能列表中的技能，且技能的组合需要考虑输入输出的数据类型兼容性。
- 如果需要使用前一个技能的输出作为下一个技能的输入，请在输入中使用 '{{{{previous_output}}}}' 占位符。
- 请确保输出是有效的 JSON（当需要执行技能时）或直接的回复（当为正常对话时），不要包含多余的解释或文本。

**用户请求**：

"{user_input}"

**示例 1（需要执行技能的情况）**：

**用户请求**：

"帮我查一下2023年全球的经济增长趋势，并绘制一个相关的图表。"

**返回**：

{{
    "summary": "用户想了解2023年全球经济增长趋势并生成图表",
    "actions": [
        {{
            "skill": "web_search",
            "input": "2023年全球经济增长趋势"
        }},
        {{
            "skill": "code_interpreter",
            "input": "{{{{previous_output}}}}；请根据以上数据生成一个折线图，显示经济增长趋势。"
        }}
    ],
    "final_response": "我已为您查询并绘制了2023年全球经济增长趋势的折线图。"
}}

**示例 2（正常对话的情况）**：

**用户请求**：

"你喜欢什么类型的音乐？"

**返回**：

"作为一个AI助理，我没有感知，但我很乐意为您推荐各种类型的音乐！您喜欢什么风格的音乐？"
"""

        # 与模型交互
        response = self.client.chat.completions.create(
            model="glm-4-airx",
            messages=[{"role": "user", "content": prompt}]
        )
        # 解析模型返回的结果
        result = response.choices[0].message.content.strip()
        try:
            # 尝试解析为 JSON
            output_data = json.loads(result)
            actions = output_data.get("actions", [])
            final_response = output_data.get("final_response", "")
            return actions, final_response
        except json.JSONDecodeError:
            # 如果无法解析为 JSON，认为是直接的回复
            return None, result

    def get_action_description(self, skill_name, input_text):
        """根据技能名称生成描述"""
        if skill_name == "web_search":
            return f"我将为您搜索：{input_text}"
        elif skill_name == "image_search":
            return f"我将为您进行桌面截图搜索，内容：{input_text}"
        elif skill_name == "code_interpreter":
            return f"我将使用代码解释器处理数据并生成图表。"
        elif skill_name == "drawing":
            return f"我将为您绘制一张图片，描述为：{input_text}"
        elif skill_name == "log_talking":
            return f"我将根据之前的对话记录来回答您的问题。"
        else:
            return f"我将执行技能：{skill_name}，输入：{input_text}"

    def process_user_input(self, user_input, emotion='NEUTRAL', is_voice=False):
        """
        处理用户输入，包括调用大模型检测技能、执行技能、生成回复等。

        :param user_input: 用户输入的文本
        :param emotion: 用户的情感（默认为 'NEUTRAL'）
        :param is_voice: 是否为语音输入
        :return: AI的回复
        """
        print("用户说:", user_input)
        sys.stdout.flush()

        with self.input_lock:
            # 添加用户输入到对话历史
            self.messages.append({"role": "user", "content": user_input})
            self.append_to_conversation_log({"role": "user", "content": user_input})
            if len(self.messages) > self.MAX_LOG_ENTRIES:
                self.messages.pop(0)

            if self.user_callback:
                self.user_callback(user_input)  # 通过用户消息回调显示在对话框中
            # 使用大模型检测需要的技能和最终回复
            actions, final_response = self.detect_action_with_large_model(user_input)

            if actions:
                # 收集动作描述
                action_descriptions = []
                for action in actions:
                    skill_name = action.get("skill")
                    input_text = action.get("input", "")
                    action_description = self.get_action_description(skill_name, input_text)
                    action_descriptions.append(action_description)

                # 生成合并后的 TTS 消息
                if len(action_descriptions) == 1:
                    tts_message = f"{action_descriptions[0]}。"
                else:
                    tts_message = "接下来，我将为您执行以下操作：\n" + "\n".join(
                        [f"{i+1}. {desc}" for i, desc in enumerate(action_descriptions)]
                    )

                # 播放 TTS 消息
                self.generate_and_play_tts(tts_message, self.emotion_mapping.get(emotion, 'lovey-dovey'))

                # 执行技能
                assistant_response_parts = []
                for action in actions:
                    skill_name = action.get("skill")
                    input_text = action.get("input", "")

                    print(f"执行技能：{skill_name}，输入：{input_text}")
                    sys.stdout.flush()

                    # 检查技能是否在预定义的技能列表中
                    if skill_name not in self.skill_names:
                        print(f"未识别的技能：{skill_name}，跳过执行。")
                        sys.stdout.flush()
                        continue

                    # 处理前一个技能的输出
                    if "{{previous_output}}" in input_text:
                        if assistant_response_parts:
                            previous_output = assistant_response_parts[-1]
                            input_text = input_text.replace("{{previous_output}}", previous_output)
                        else:
                            print(f"无法获取前一个技能的输出，跳过技能：{skill_name}")
                            sys.stdout.flush()
                            continue

                    # 执行技能
                    if skill_name == "web_search":
                        result = self.execute_web_search(input_text)
                    elif skill_name == "image_search":
                        default_description = "请描述一下这张图里面的内容"
                        result = self.execute_image_search(user_text=default_description, image_path=None)
                    elif skill_name == "code_interpreter":
                        result = self.execute_code_interpreter(input_text)
                    elif skill_name == "drawing":
                        result = self.execute_drawing(input_text)
                    elif skill_name == "log_talking":
                        result = self.execute_history_search(input_text)
                    else:
                        # 处理未定义的技能
                        print(f"未定义的技能：{skill_name}，跳过执行。")
                        continue

                    # 输出技能执行结果
                    print(f"技能 {skill_name} 的执行结果：{result}")
                    sys.stdout.flush()

                    # 根据执行结果生成回复
                    if result.get('type') == 'text':
                        assistant_response_parts.append(result.get('content', ''))
                    elif result.get('type') == 'image_path':
                        assistant_response_parts.append(f"已生成图像：{result.get('content', '')}")
                    elif result.get('type') == 'error':
                        assistant_response_parts.append(f"执行技能 {skill_name} 时出错：{result.get('content', '')}")

                # 合并所有技能的输出作为AI的回答
                assistant_final_response = "\n".join(assistant_response_parts) if assistant_response_parts else final_response

                # 添加AI的回答到对话历史
                self.messages.append({"role": "assistant", "content": assistant_final_response})
                self.append_to_conversation_log({"role": "assistant", "content": assistant_final_response})
                if len(self.messages) > self.MAX_LOG_ENTRIES:
                    self.messages.pop(0)

                # 通过回调将回复发送给前端
                if self.ai_callback:
                    self.ai_callback(assistant_final_response)

                return assistant_final_response
            else:
                # 没有需要执行的技能，直接回复
                assistant_reply = final_response
                print("AI:", assistant_reply)
                sys.stdout.flush()
                self.messages.append({"role": "assistant", "content": assistant_reply})
                self.append_to_conversation_log({"role": "assistant", "content": assistant_reply})
                if len(self.messages) > self.MAX_LOG_ENTRIES:
                    self.messages.pop(0)

           
                
                # 通过回调将回复发送给前端
                if self.ai_callback:
                    self.ai_callback(assistant_reply)

                return assistant_reply


    # -------------- 以下为语音处理和TTS相关函数 --------------

    def extract_language_emotion_content(self, text):
        """提取文本中的情感标签和纯净内容"""
        pattern = r'<\|([^|]+)\|>'
        tags = re.findall(pattern, text)

        print(f"提取的标签: {tags}")

        if len(tags) > 1:
            emotion = tags[1]
        else:
            emotion = 'neutral'

        content = re.sub(r'(<\|[^|]+\|>)+', '', text).strip()
        emotion = emotion.strip()

        print(f"提取的内容: {content}")
        print(f"检测到的情感: {emotion}")

        return content, emotion

    def transcribe_audio(self, file_path):
        """将音频文件转录为文本"""
        res = self.model.generate(
            input=file_path,
            cache={},
            language="auto",
            use_itn=False,
            ban_emo_unk=True,
            batch_size_s=60,
            merge_vad=True,
            merge_length_s=15,
        )
        if len(res) > 0 and "text" in res[0]:
            text = res[0]["text"]
            content, emotion = self.extract_language_emotion_content(text)
            return content, emotion
        else:
            return None, None

    def execute_history_search(self, query):
        """根据历史对话记录回答用户问题"""
        try:
            history_content = self.load_conversation_log()
            print(f"加载的记录：{history_content}")

            history_contents = [msg['content'] for msg in history_content]
            history_summary = "\n".join(history_contents)

            if not history_summary:
                return {"type": "error", "content": "没有有效的历史记录可供处理。"}

            user_query = f"请根据之前的对话记录回答：{query}\n以下是相关记录：\n{history_summary}"

            print(f"发送给大语言模型的输入：{user_query}")

            response = self.client.chat.completions.create(
                model="glm-4-airx",
                messages=[{"role": "user", "content": user_query}]
            )

            result = response.choices[0].message.content.strip()

            return {"type": "text", "content": result}

        except Exception as e:
            print(f"处理历史记录请求时出错: {e}")
            return {"type": "error", "content": "处理历史记录请求时出错"}

    def execute_web_search(self, query):
        """执行网页搜索技能"""
        try:
            result = subprocess.run(
                ["python", "skill_web_search.py", query],
                check=True,
                capture_output=True,
                text=True,
                cwd="skill"
            )
            output_text = result.stdout.strip()
            if not output_text:
                print(f"web_search 子进程没有输出内容，标准错误输出为：\n{result.stderr}")
                return {"type": "error", "content": "web_search 技能执行出错，未获取到输出。"}
            output_data = json.loads(output_text)
            return output_data
        except subprocess.CalledProcessError as e:
            print(f"搜索技能执行出错: {e}")
            print(f"子进程错误信息:\n{e.stderr}")
            return {"type": "error", "content": "搜索技能执行出错"}
        except json.JSONDecodeError as e:
            print(f"解析搜索技能输出时发生错误: {e}")
            print(f"子进程标准输出:\n{output_text}")
            return {"type": "error", "content": "解析搜索技能输出时发生错误"}

    def execute_image_search(self, user_text="", image_path=None):
        """
        执行图片搜索技能。

        :param user_text: 用户输入的文本，用于提供上下文或描述。
        :param image_path: 图片文件路径。如果为 None，则进行截图并使用默认描述。
        :return: 技能执行结果
        """
        if image_path:
            cmd = ["python", "skill_image_search.py", user_text, image_path]
        else:
            # 使用默认描述
            default_description = "请描述一下这张图里面的内容"
            cmd = ["python", "skill_image_search.py", default_description]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd="skill"
            )
            output_text = result.stdout.strip()
            if not output_text:
                print(f"image_search 子进程没有输出内容，标准错误输出为：\n{result.stderr}")
                return {"type": "error", "content": "image_search 技能执行出错，未获取到输出。"}
            output_data = json.loads(output_text)

            # 如果输出数据包含图片路径
            if output_data.get('image_path'):
                image_full_path = output_data.get('image_path')
                # 发送以 [IMAGE] 开头的消息给前端
                if self.ai_callback:
                    self.ai_callback(f"[IMAGE]{image_full_path}")

            return output_data
        except subprocess.CalledProcessError as e:
            print(f"图片搜索技能执行出错: {e}")
            print(f"子进程错误信息:\n{e.stderr}")
            return {"type": "error", "content": "图片搜索技能执行出错"}
        except json.JSONDecodeError as e:
            print(f"解析图片搜索技能输出时发生错误: {e}")
            print(f"子进程标准输出:\n{output_text}")
            return {"type": "error", "content": "解析图片搜索技能输出时发生错误"}
            

    def execute_code_interpreter(self, prompt_text):
        """执行代码解释器技能"""
        try:
            result = subprocess.run(
                ["python", "skill_code_interpreter.py", prompt_text],
                check=True,
                capture_output=True,
                text=True,
                cwd="skill"
            )
            execution_output = result.stdout.strip()
            if not execution_output:
                print(f"code_interpreter 子进程没有输出内容，标准错误输出为：\n{result.stderr}")
                return {"type": "error", "content": "code_interpreter 技能执行出错，未获取到输出。"}
            output_data = json.loads(execution_output)
            return output_data
        except subprocess.CalledProcessError as e:
            print(f"代码解释器技能执行出错: {e}")
            print(f"子进程错误信息:\n{e.stderr}")
            return {"type": "error", "content": "代码解释器技能执行出错"}
        except json.JSONDecodeError as e:
            print(f"解析代码解释器输出时发生错误: {e}")
            print(f"子进程标准输出:\n{execution_output}")
            return {"type": "error", "content": "解析代码解释器输出时发生错误"}

    def execute_drawing(self, description):
        """执行画图技能"""
        try:
            result = subprocess.run(
                ["python", "skill_drawing.py", description],
                check=True,
                capture_output=True,
                text=True,
                cwd="skill"
            )
            image_path = result.stdout.strip()

            if not image_path:
                print(f"子进程没有返回图像路径，标准错误输出为：\n{result.stderr}")
                return {"type": "error", "content": "画图技能执行出错，未获取到图像路径。"}

            # 检查是否成功生成图像
            if os.path.exists(os.path.join("skill", image_path)):
                image_full_path = os.path.join("skill", image_path)
                #image = Image.open(image_full_path)
                #image.show()

                output_data = {
                    "type": "image_path",
                    "content": image_full_path
                }

                            # 发送以 [IMAGE] 开头的消息给前端
                if self.ai_callback:
                    self.ai_callback(f"[IMAGE]{image_full_path}")
                return output_data
            else:
                print(f"子进程输出：{result.stdout}")
                print(f"子进程错误信息：{result.stderr}")
                return {"type": "error", "content": "未找到生成的图像文件"}

        except subprocess.CalledProcessError as e:
            print(f"画图技能执行出错: {e}")
            print(f"子进程错误信息:\n{e.stderr}")
            return {"type": "error", "content": "画图技能执行出错"}

    # -------------- 语音合成（TTS）相关 --------------

    def generate_and_play_tts(self, text, tts_emotion):
        """生成并播放TTS语音"""
        with self.ai_speaking_lock:
            self.is_AI_speaking = True  # AI开始说话
            self.skip_event.clear()      # 重置跳过事件
            if self.communicator:
                self.communicator.ai_speaking_started.emit()

        appid = self.appidcon
        access_token = self.tokencon
        cluster = "volcano_tts"
        voice_type = self.voice_type
        host = "openspeech.bytedance.com"
        api_url = f"https://{host}/api/v1/tts"
        header = {"Authorization": f"Bearer;{access_token}"}

        # 预处理文本
        cleaned_text = text
        max_length = 200
        if len(cleaned_text) > max_length:
            cleaned_text = cleaned_text[:max_length]

        request_json = {
            "app": {
                "appid": appid,
                "token": access_token,
                "cluster": cluster
            },
            "user": {
                "uid": self.user_uid
            },
            "audio": {
                "voice_type": voice_type,
                "encoding": "mp3",
                "speed_ratio": 1.2,
                "volume_ratio": 1.0,
                "pitch_ratio": 1.1,
                "emotion": tts_emotion,
                "language": "zh"
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": str(cleaned_text),
                "text_type": "plain",
                "operation": "query",
                "with_frontend": 1,
                "frontend_type": "unitTson"
            }
        }

        try:
            resp = requests.post(api_url, json=request_json, headers=header)
            response_data = resp.json()

            if "data" in response_data:
                data = response_data["data"]
                with open("tts_output.mp3", "wb") as file_to_save:
                    file_to_save.write(base64.b64decode(data))
                audio = AudioSegment.from_mp3("tts_output.mp3")

                raw_data = audio.raw_data
                sample_rate = audio.frame_rate
                num_channels = audio.channels
                bytes_per_sample = audio.sample_width

                play_obj = sa.play_buffer(raw_data, num_channels, bytes_per_sample, sample_rate)
                print("AI开始说话")

                while play_obj.is_playing():
                    if self.skip_event.is_set():
                        play_obj.stop()
                        print("AI说话被跳过")
                        self.skip_event.clear()
                        break
                    time.sleep(0.1)

                print("AI结束说话")
                os.remove("tts_output.mp3")
            else:
                print("TTS 响应中没有找到数据")
                if "error_code" in response_data and "error_msg" in response_data:
                    print(f"错误代码：{response_data['error_code']}, 错误信息：{response_data['error_msg']}")
                else:
                    print("无法获取错误信息，请检查请求参数和响应内容。")

        except Exception as e:
            print(f"TTS请求错误: {e}")
        finally:
            with self.ai_speaking_lock:
                self.is_AI_speaking = False  # AI结束说话
                self.skip_event.clear()       # 确保事件被清除
                if self.communicator:
                    self.communicator.ai_speaking_finished.emit()

    # -------------- 录音相关 --------------

    def save_recorded_frames(self, frames):
        """保存录制的音频帧到文件"""
        wf = wave.open(self.WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def monitor_mic_and_process(self):
        """监听麦克风并处理语音输入"""
        p = pyaudio.PyAudio()
        stream = p.open(format=self.FORMAT,
                        channels=self.CHANNELS,
                        rate=self.RATE,
                        input=True,
                        frames_per_buffer=self.FRAME_SIZE)
        vad = webrtcvad.Vad(self.VAD_AGGRESSIVENESS)

        print("开始监听麦克风...")

        while True:
            frames = []
            speech_started = False
            num_silent_frames = 0
            num_voice_frames = 0
            num_voice_frames_threshold = 3

            while True:
                with self.ai_speaking_lock:
                    if self.is_AI_speaking:
                        # AI正在说话，跳过当前帧处理
                        time.sleep(0.1)
                        continue

                try:
                    frame = stream.read(self.FRAME_SIZE, exception_on_overflow=False)
                except Exception as e:
                    print(f"音频读取错误：{e}")
                    continue

                if len(frame) == 0:
                    print("未读取到音频数据，跳过本次循环。")
                    continue

                is_speech = vad.is_speech(frame, self.RATE)

                audio_data = np.frombuffer(frame, dtype=np.int16)

                if audio_data.size == 0:
                    print("音频数据为空，跳过本次循环。")
                    continue

                rms = np.sqrt(np.mean(audio_data.astype(np.float64) ** 2))
                if np.isnan(rms):
                    print("计算得到无效的 RMS 值，跳过本次循环。")
                    continue

                volume_threshold = 1000
                is_loud_enough = rms > volume_threshold

                if is_speech and is_loud_enough:
                    num_voice_frames += 1
                    if not speech_started and num_voice_frames >= num_voice_frames_threshold:
                        speech_started = True
                        self.on_speaking_detected()
                    if speech_started:
                        frames.append(frame)
                        num_silent_frames = 0
                else:
                    num_voice_frames = 0
                    if speech_started:
                        num_silent_frames += 1
                        frames.append(frame)
                        if num_silent_frames > self.NUM_SILENT_FRAMES_THRESHOLD:
                            self.on_long_silence_detected()
                            break

            if frames:
                with self.ai_speaking_lock:
                    if self.is_AI_speaking:
                        print("AI正在说话，忽略此语音输入。")
                        continue

                self.save_recorded_frames(frames)
                user_input, emotion = self.transcribe_audio(self.WAVE_OUTPUT_FILENAME)
                if user_input:
                    self.process_user_input(user_input, emotion, is_voice=True)

            else:
                print("未检测到有效语音，继续监听。")


    def on_speaking_detected(self):
        """检测到说话事件"""
        print("检测到说话")

    def on_long_silence_detected(self):
        """检测到长时间静音事件"""
        print("长时间静音")

    def start(self):
        """启动语音助手"""
        mic_thread = threading.Thread(target=self.monitor_mic_and_process, daemon=True)
        mic_thread.start()
        print("语音助手已启动，开始监听语音输入。")

    # -------------- 其他技能执行方法可继续添加 --------------

