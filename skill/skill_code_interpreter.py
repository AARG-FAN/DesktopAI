from zhipuai import ZhipuAI
import json
import sys
import subprocess
import os

# 初始化 API 客户端（请填写您自己的 API Key）
client = ZhipuAI(api_key="75d95ba977d5df8c15be3ae69156ef98.82asPfVz9OLfAdeZ")  # 请替换为您的 API Key

def code_interpret(prompt_text):
    try:
        # 构建消息列表
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt_text
                    }
                ]
            }
        ]

        # 调用 API，启用流式输出
        response = client.chat.completions.create(
            model="glm-4-alltools",
            messages=messages,
            stream=True,
            tools=[
                {
                    "type": "code_interpreter"
                }
            ]
        )

        # 初始化变量
        assistant_reply = ""
        code_input = ""
        code_outputs = []

        # 处理流式响应
        for chunk in response:
            if 'choices' in chunk and chunk['choices']:
                choice = chunk['choices'][0]
                delta = choice.get('delta', {})
                # 处理 assistant 回复
                if delta.get('role') == 'assistant':
                    if 'content' in delta and delta['content']:
                        assistant_reply += delta['content']
                # 处理工具调用
                if 'tool_calls' in delta and delta['tool_calls']:
                    for tool_call in delta['tool_calls']:
                        if tool_call['type'] == 'code_interpreter':
                            # 获取生成的代码
                            code_input += tool_call['code_interpreter'].get('input', '')
                # 检查是否需要结束
                if choice.get('finish_reason') == 'stop':
                    break

        # 检查是否生成了代码
        if not code_input.strip():
            output_data = {
                "type": "error",
                "content": "未生成代码，无法执行。"
            }
            print(json.dumps(output_data, ensure_ascii=False))
            return

        # 将生成的代码保存到文件
        code_file = "generated_code.py"
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code_input)

        # 执行生成的代码
        import subprocess
        execution_result = subprocess.run(
            ["python", code_file],
            capture_output=True,
            text=True
        )

        # 获取代码执行的输出
        execution_output = execution_result.stdout.strip()
        execution_error = execution_result.stderr.strip()

        # 删除临时的代码文件
        import os
        os.remove(code_file)

        # 构建输出结果
        if execution_result.returncode == 0:
            output_data = {
                "type": "text",
                "content": execution_output
            }
        else:
            output_data = {
                "type": "error",
                "content": f"代码执行出错：{execution_error}"
            }

        # 输出结果
        print(json.dumps(output_data, ensure_ascii=False))

    except Exception as e:
        # 捕获并输出错误信息
        error_data = {
            "type": "error",
            "content": f"执行 code_interpreter 时发生错误: {e}"
        }
        print(json.dumps(error_data, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt_text = sys.argv[1]
        code_interpret(prompt_text)
    else:
        print(json.dumps({"type": "error", "content": "未提供输入文本"}, ensure_ascii=False))
