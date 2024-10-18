import asyncio
import io
import os
import uuid
from pydub import AudioSegment
from spike.image_analysis import analyze_image
from spike.llm_conversation import llm_reply
from spike.text_segmenter import segment_text
from spike.volcengine_streaming_asr import recognize
from spike.volcengine_websocket_tts import tts

image_description_map = { "2890e8fc-66b0-4404-9b00-ffae791be000": "题目描述: 这是一份四年级数学限时练习题的照片，图片中一共有5道数学题，分别为： 1. $2024\times2025\div} 111+2024\times65+37+6.28=$_____ 2. 有4、5、6、7、8克的砝码各1个，丢失了其中一个砝码，结果天平无法称出19克的质量(砝码必须放在天平的同一侧)。则丢失的砝码是_____克。 3. 20只质量相同的猫一组，18只质量相同的狗一组，两组共112千克，如果从两组中分别取8只猫与8只狗相交换，两组质量就相同了，每只狗比猫多_____千克。 4. 李老师在家和学校之间往返，去的时候步行，回来的时候骑车，共需要43分钟；如果小明往返都是骑车，则只需要15分钟。其中步行的速度保持一致，骑车的速度也保持一致。那么如果小明往返都是步行，需要_____分钟。 5. 如图所示的阴影部分是一枚手里剑的图形。已知点A、B、C、D、M、N、K、L都是相应的大正方形边上的中点，图中最小的正方形ABCD的边长是4厘米，那么这枚手里剑的面积是_____平方厘米。"}

def upload_image(image):
    image_id = str(uuid.uuid4())
    
    temp_image_path = f"temp_{image_id}.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(image.file.read())
    
    description = analyze_image(temp_image_path)
    
    image_description_map[image_id] = description
    
    os.remove(temp_image_path)

    return image_id, description


async def process_audio(audio_data, image_id, websocket):
    audio_filename = save_input_audio_file(audio_data)

    input_text = await recognize(audio_filename)
    if input_text == "":
        await websocket.send_bytes(retryvoice_data())
    else:
        stream_response = llm_reply(input_text, image_description_map[image_id])

        segments = segment_text(stream_response, segment_size=2)

        output_texts = ""
        _order = 0

        for segment in segments:
            _order += 1
            output_texts += segment
            print(f"output_texts: {output_texts}")
            print(f"order: {_order}, tts_text: {segment}")

            audio_bytes = await tts(text=segment)
            await websocket.send_bytes(audio_bytes)

    # 清理临时音频文件
    os.remove(audio_filename)

def save_input_audio_file(audio_data):
    audio_filename = f"./audio/audio_{uuid.uuid4()}.wav"

    audio = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")  # 假设格式为 webm，根据实际情况调整
    
    audio.export(audio_filename, format="wav", codec="pcm_s16le")
    return audio_filename

async def generate_audio_stream():
    while True:
        audio_bytes = await audio_queue.get()
        yield audio_bytes

def retryvoice_data():
    filename = "./audio/retryvoice.mp3"
    with open(filename, "rb") as f:
        return f.read()
