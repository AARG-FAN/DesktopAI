import base64
import sys
from zhipuai import ZhipuAI
import json

# 初始化 ZhipuAI 客户端
client = ZhipuAI(api_key="75d95ba977d5df8c15be3ae69156ef98.82asPfVz9OLfAdeZ")  # 填写您自己的APIKey



def web_search(query):
    try:
        # 发送请求到 ZhipuAI，执行 web 搜索
        response = client.chat.completions.create(
            model="glm-4-alltools",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": query
                        }
                    ]
                }
            ],
            max_tokens=1000,
            stream=True,
            tools=[
                {
                    "type": "web_browser",
                    "web_browser": {
                        "browser": "auto"
                    }
                }
            ]
        )

        # 初始化一个空字符串来存储完整的响应内容
        full_response = ""

        # 逐行提取并累积搜索结果中的文本内容
        for chunk in response:
            if hasattr(chunk, 'choices') and chunk.choices:
                for choice in chunk.choices:
                    if hasattr(choice.delta, 'content') and choice.delta.content:
                        full_response += choice.delta.content

        # 移除首尾空白字符
        full_response = full_response.strip()

        # 将结果封装为 JSON 格式并打印
        output_data = {
            "type": "text",
            "content": full_response
        }
        print(json.dumps(output_data, ensure_ascii=False))

    except Exception as e:
        # 输出错误信息
        error_data = {
            "type": "error",
            "content": f"执行 web_search 时发生错误: {e}"
        }
        print(json.dumps(error_data, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query_text = sys.argv[1]
        web_search(query_text)
    else:
        print(json.dumps({"type": "error", "content": "未提供查询内容"}, ensure_ascii=False))