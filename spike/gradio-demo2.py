import gradio as gr
import random
import time
from openai import OpenAI
import os
import base64

client = OpenAI(
    api_key=os.environ.get("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

conversation_history = []
MAX_CONVERSATION_ROUND = 10
MAX_CONVERSATION_HISTORY_SIZE = 2 * MAX_CONVERSATION_ROUND
last_analyzed_image = None

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_image(image):
    print(f"接收到的图片路径: {image}")
    
    # 确保文件存在
    if not os.path.exists(image):
        return f"错误：文件 '{image}' 不存在"
    
    try:
        base64_image = encode_image(image)
        response = client.chat.completions.create(
            model="glm-4v",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "完整描述题目内容"
                        }
                    ]
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"分析图片时出错：{str(e)}"

def chat(message, image, history):
    global conversation_history, last_analyzed_image
    
    if image is not None and image != last_analyzed_image:
        homework_description = analyze_image(image)
        system_prompt = f"""你是辅导家庭作业的AI助手。
## 作业描述如下：
{homework_description}
## 要求：
可以尝试理解一下用户不清楚的原因，逐步引导用户一步步思考。整个过程会采用一问一答的方式，过程中都不能告诉答案，也不需要一次性全部回复解题思路，需要一步步引导用户思考然后基于用户的思考再继续回复。
"""

        conversation_history = [{"role": "system", "content": system_prompt}]
        last_analyzed_image = image
    elif not conversation_history:
        return "请先上传一张作业图片。"
    
    conversation_history = conversation_history[-MAX_CONVERSATION_HISTORY_SIZE:]
    conversation_history.append({"role": "user", "content": message})
    history.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model="GLM-4-AirX",
        messages=conversation_history,
        stream=True
    )
    
    partial_message = ""
    history.append({"role": "assistant", "content": partial_message})
    for chunk in response:
        if chunk.choices[0].delta.content:
            partial_message += chunk.choices[0].delta.content
            history[-1]["content"] = partial_message
            yield history
    
    conversation_history.append({"role": "assistant", "content": partial_message})


with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            msg = gr.Textbox(lines=2, label="您的消息")
            img =gr.Image(type="filepath", label="上传作业图片")
            submit = gr.Button("提交")
        with gr.Column():
            chatbot = gr.Chatbot(type="messages")
            # ai = gr.Textbox(label="AI 回复", lines=10)

    submit.click(chat, [msg, img, chatbot], [chatbot])

demo.launch()