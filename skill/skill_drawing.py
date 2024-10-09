
from zhipuai import ZhipuAI
import requests
import os
import json
import time

# 初始化 API 客户端（请填写您自己的 API Key）
client = ZhipuAI(api_key="75d95ba977d5df8c15be3ae69156ef98.82asPfVz9OLfAdeZ") 

IMAGE_DIR = "image"
os.makedirs(IMAGE_DIR, exist_ok=True)


def draw_image(description):
    try:
        response = client.images.generations(
            model="cogview-3-plus",  # 使用官方示例中的模型名称
            prompt=description,
        )

        # 检查响应数据结构
        if response and response.data and len(response.data) > 0:
            image_url = response.data[0].url
            # 下载图像并保存
            image_data = requests.get(image_url).content
            timestamp = int(time.time() * 1000)
            image_path = os.path.join(IMAGE_DIR, f"generated_image_{timestamp}.jpg")
            with open(image_path, "wb") as f:
                f.write(image_data)
            print(image_path)  # 将图像路径打印出来，供主程序使用
        else:
            print("未能获取生成的图像 URL。")
    except Exception as e:
        print(f"生成图像时发生错误: {e}")

if __name__ == "__main__":
        import sys
        if len(sys.argv) > 1:
            description = sys.argv[1]
            draw_image(description)
        else:
            print("未提供描述内容，技能结束。")
