import base64
import sys
from zhipuai import ZhipuAI
import os
from grabscreen import capture_screenshot  # 导入截图功能
import json

def image_search(user_text, image_path=None):
    # 确定使用的图像
    if image_path:
        if not os.path.exists(image_path):
            error_message = f"提供的图片文件不存在: {image_path}"
            print(json.dumps({"type": "error", "content": error_message}, ensure_ascii=False))
            return
        img_path = image_path
    else:
        # 生成截图
        img_path = "screenshot.jpg"
        capture_screenshot(output_path=img_path)  # 调用 grabscreen.py 的截图功能

        # 检查截图是否成功
        if not os.path.exists(img_path):
            error_message = "截图失败，未找到截图文件。"
            print(json.dumps({"type": "error", "content": error_message}, ensure_ascii=False))
            return

    # 编码图片为 Base64
    try:
        with open(img_path, 'rb') as img_file:
            img_base = base64.b64encode(img_file.read()).decode('utf-8')
    except Exception as e:
        error_message = f"编码图片失败: {e}"
        print(json.dumps({"type": "error", "content": error_message}, ensure_ascii=False))
        return

    # 初始化API客户端
    client = ZhipuAI(api_key="75d95ba977d5df8c15be3ae69156ef98.82asPfVz9OLfAdeZ")  # 请填写您自己的APIKey

    # 发送请求到大模型
    try:
        response = client.chat.completions.create(
            model="glm-4v-plus",  # 填写需要调用的模型名称
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": img_base
                            }
                        },
                        {
                            "type": "text",
                            "text": user_text  # 使用用户传递的文本作为 prompt
                        }
                    ]
                }
            ]
        )
        description = response.choices[0].message.content.strip()
        # 将结果封装为 JSON，并打印
        output_data = {
            "type": "text",
            "content": description
        }
        print(json.dumps(output_data, ensure_ascii=False))
    except Exception as e:
        error_message = f"调用大模型 API 时出错: {e}"
        print(json.dumps({"type": "error", "content": error_message}, ensure_ascii=False))
    finally:
        # 删除截图文件（如果是截图的话）
        if not image_path and os.path.exists(img_path):
            os.remove(img_path)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_text = sys.argv[1]
        image_path = sys.argv[2] if len(sys.argv) > 2 else None
        image_search(user_text, image_path)
    else:
        error_message = "未提供用户请求的文本，技能结束。"
        print(json.dumps({"type": "error", "content": error_message}, ensure_ascii=False))
