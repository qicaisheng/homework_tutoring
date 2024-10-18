import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
import os
from typing import AsyncGenerator, Generator
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/",
)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


async def analyze_image_async(image_path) -> AsyncGenerator[str, None]:
    executor = ThreadPoolExecutor()

    loop = asyncio.get_event_loop()
    for chunk in await loop.run_in_executor(executor, analyze_image, image_path):
        yield chunk

        
def analyze_image(image) -> Generator[str, None, None]:
    print(f"接收到的图片路径: {image}")
    
    # 确保文件存在
    if not os.path.exists(image):
        yield f"错误：文件 '{image}' 不存在"
        return
    
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
            ],
            stream=True
        )
        partial_message = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                partial_message += chunk.choices[0].delta.content
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"分析图片时出错：{str(e)}"
