import asyncio
from concurrent.futures import ThreadPoolExecutor
import io
import os
import uuid
import time
from fastapi import WebSocketDisconnect
from pydub import AudioSegment
from spike.image_analysis import analyze_image, analyze_image_async
from spike.llm_conversation import llm_reply
from spike.text_segmenter import segment_text
from spike.volcengine_streaming_asr import recognize
from spike.volcengine_websocket_tts import tts
import json

image_description_map = { "2890e8fc-66b0-4404-9b00-ffae791be000": "题目描述: 这是一份四年级数学限时练习题的照片，图片中一共有5道数学题，分别为： 1. $2024\times2025\div} 111+2024\times65+37+6.28=$_____ 2. 有4、5、6、7、8克的砝码各1个，丢失了其中一个砝码，结果天平无法称出19克的质量(砝码必须放在天平的同一侧)。则丢失的砝码是_____克。 3. 20只质量相同的猫一组，18只质量相同的狗一组，两组共112千克，如果从两组中分别取8只猫与8只狗相交换，两组质量就相同了，每只狗比猫多_____千克。 4. 李老师在家和学校之间往返，去的时候步行，回来的时候骑车，共需要43分钟；如果小明往返都是骑车，则只需要15分钟。其中步行的速度保持一致，骑车的速度也保持一致。那么如果小明往返都是步行，需要_____分钟。 5. 如图所示的阴影部分是一枚手里剑的图形。已知点A、B、C、D、M、N、K、L都是相应的大正方形边上的中点，图中最小的正方形ABCD的边长是4厘米，那么这枚手里剑的面积是_____平方厘米。"}

async def upload_image(image):
    image_id = str(uuid.uuid4())
    
    temp_image_path = f"temp_{image_id}.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(image.file.read())
    
    asyncio.create_task(process_image(image_id, temp_image_path))

    return image_id


async def process_image(image_id, temp_image_path):
    try:
        image_description_map[image_id] = ""
        description = await analyze_image_async(temp_image_path)
        image_description_map[image_id] = description
    finally:
        os.remove(temp_image_path)


async def process_audio(audio_data, user_id, image_id, websocket):
    try:
        start_time = time.time()
        
        # 保存上传的音频文件
        save_start_time = time.time()
        audio_filename = save_input_audio_file(audio_data)
        save_end_time = time.time()
        print(f"保存上传音频文件耗时: {save_end_time - save_start_time:.2f}秒")

        # ASR
        asr_start_time = time.time()
        input_text = await recognize(audio_filename)
        asr_end_time = time.time()
        print(f"ASR耗时: {asr_end_time - asr_start_time:.2f}秒")

        if input_text == "":
            await websocket.send_bytes(retryvoice_data())
        else:
            # LLM reply
            llm_start_time = time.time()
            stream_response = llm_reply(user_id, input_text, image_description_map.get(image_id, ""))
            llm_end_time = time.time()
            print(f"LLM reply耗时: {llm_end_time - llm_start_time:.2f}秒")

            segment_start_time = time.time()
            segments = segment_text(stream_response, segment_size=2)
            segment_end_time = time.time()
            print(f"分段文本耗时: {segment_end_time - segment_start_time:.2f}秒")

            output_texts = ""
            _order = 0

            # TTS
            tts_start_time = time.time()
            for segment in segments:
                _order += 1
                output_texts += segment
                print(f"output_texts: {output_texts}")
                print(f"order: {_order}, tts_text: {segment}")

                segment_tts_start_time = time.time()
                audio_bytes = await tts(text=segment)
                segment_tts_end_time = time.time()
                print(f"第{_order}段文本TTS耗时: {segment_tts_end_time - segment_tts_start_time:.2f}秒")
                print(f"第{_order}段文本TTS耗时)(距离初始TTS): {segment_tts_end_time - tts_start_time:.2f}秒")
                
                websocket_send_start_time = time.time()
                await websocket.send_bytes(audio_bytes)
                send_end_time = time.time()
                print(f"第{_order}段音频发送耗时: {send_end_time - websocket_send_start_time:.2f}秒")
            tts_end_time = time.time()
            print(f"TTS总耗时: {tts_end_time - tts_start_time:.2f}秒")

        end_time = time.time()
        print(f"处理音频总耗时: {end_time - start_time:.2f}秒")

    except WebSocketDisconnect:
        print("WebSocket 连接已断开")
    except Exception as e:
        print(f"处理音频时出错: {e}")
        try:
            error_message = json.dumps({
                "type": "error",
                "message": "处理音频时出错，请重试"
            })
            await websocket.send_text(error_message)
        except RuntimeError:
            pass  # 忽略已关闭的WebSocket连接
    # finally:
        # 清理临时音频文件
        # if 'audio_filename' in locals():
            # os.remove(audio_filename)


def save_input_audio_file(audio_data):
    audio_filename = f"./audio/audio_{uuid.uuid4()}.wav"

    # audio = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")  # 假设格式为 webm，根据实际情况调整
    
    # audio.export(audio_filename, format="wav", codec="pcm_s16le")
    
    with open(audio_filename, "wb") as f:
        f.write(audio_data)

    return audio_filename


def retryvoice_data():
    filename = "./audio/retryvoice.mp3"
    with open(filename, "rb") as f:
        return f.read()
