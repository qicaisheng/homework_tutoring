import gradio as gr
from openai import OpenAI
import os
import base64
from text_segmenter import segment_text
from volcengine_websocket_tts import tts

client = OpenAI(
    api_key=os.environ.get("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

# openai_client = OpenAI()

conversation_history = []
gradio_chatbot_histoy = []
MAX_CONVERSATION_ROUND = 10
MAX_CONVERSATION_HISTORY_SIZE = 2 * MAX_CONVERSATION_ROUND
last_analyzed_image = None
homework_description = None

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
                            "text": "完整描述题目内容，如果题目带图形，描述图形中的几何信息"
                        }
                    ]
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"分析图片时出错：{str(e)}"


def generate_html(audio_base64: str) -> str:
    """生成 HTML，用于音频播放"""
    return f"""
    <audio id="player" controls autoplay>
        <source src="{audio_base64}" type="audio/mp3">
        Your browser does not support the audio element.
    </audio>
    <script>
    const player = document.getElementById('player');
    player.onended = async () => {{
        const response = await fetch('/next_audio');  // 获取下一个音频文件的 Base64 数据
        const nextAudio = await response.text();
        if (nextAudio) {{
            player.src = nextAudio;
            player.play();
        }}
    }};
    </script>
    """

def llm_reply(message, image):
    system_prompt = """请你作为一个小学数学老师，擅长教育学生数学思维，帮助引导一步步解答数学题。过程中可以引导学生列出方程式，但是不要告诉答案。每次启发式提问不要超过2个，每次回答保持75字以内。
## 作业描述如下：
{homework_description}
"""
    global conversation_history, gradio_chatbot_histoy, last_analyzed_image, homework_description
    
    if image is not None and image != last_analyzed_image:
        homework_description = analyze_image(image)
        last_analyzed_image = image
    elif not conversation_history:
        return "请先上传一张作业图片。"

    initial_message = {
        "role": "system", 
        "content": system_prompt.format(homework_description=homework_description)
    }

    conversation_history = conversation_history[-MAX_CONVERSATION_HISTORY_SIZE:]
    gradio_chatbot_histoy = gradio_chatbot_histoy[-MAX_CONVERSATION_HISTORY_SIZE:]
    conversation_history.append({"role": "user", "content": message})
    gradio_chatbot_histoy.append([message, None])
    
    response = client.chat.completions.create(
        model="GLM-4-AirX",
        # model="gpt-4o",
        messages=[initial_message] + conversation_history,
        stream=True
    )
    
    partial_message = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content)
            partial_message += chunk.choices[0].delta.content
            yield chunk.choices[0].delta.content
    
    conversation_history.append({"role": "assistant", "content": partial_message})
    gradio_chatbot_histoy[-1][1] = partial_message



async def reply(text, image):
    llm_response = llm_reply(text, image)
    segments = segment_text(llm_response, segment_size=2)
    for segment in segments:
        print(f"segment: {segment}")
        audio_file = await tts(text=segment)
        yield generate_html(audio_file), gradio_chatbot_histoy


with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            img =gr.Image(type="filepath", label="上传作业图片")
            msg = gr.Textbox(lines=2, label="输入问题")
            submit = gr.Button("提交")
            audio_player = gr.HTML()

        with gr.Column():
            chatbot = gr.Chatbot()
    submit.click(reply, inputs=[msg, img], outputs=[audio_player, chatbot])

demo.launch()