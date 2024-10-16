import asyncio
import base64
import io
import os
import uuid
from pydub import AudioSegment
from spike.image_analysis import analyze_image
from spike.llm_conversation import llm_reply
from spike.text_segmenter import segment_text
from spike.volcengine_streaming_asr import recognize
from spike.volcengine_websocket_tts import tts

image_description_map = {}
audio_queue = asyncio.Queue()

def upload_image(image):
    image_id = str(uuid.uuid4())
    
    temp_image_path = f"temp_{image_id}.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(image.file.read())
    
    description = analyze_image(temp_image_path)
    
    image_description_map[image_id] = description
    
    os.remove(temp_image_path)

    return image_id, description


async def process_audio(audio_data, image_id):
    audio_filename = save_input_audio_file(audio_data)

    input_text = await recognize(audio_filename)

    stream_response = llm_reply(input_text, image_description_map[image_id])

    segments = segment_text(stream_response, segment_size=2)

    output_texts = ""
    _order = 0

    for segment in segments:
        output_texts += segment
        print(f"output_texts: {output_texts}")
        print(f"order: {_order}, tts_text: {segment}")

        audio_base64 = await tts(text=segment)
        await audio_queue.put(audio_base64)

def save_input_audio_file(audio_data):
    audio_filename = f"./audio/audio_{uuid.uuid4()}.wav"

    audio_bytes = base64.b64decode(audio_data)

    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="webm")  # 假设格式为 webm，根据实际情况调整
    
    audio.export(audio_filename, format="wav", codec="pcm_s16le")
    return audio_filename

async def generate_audio_stream():
    while True:
        audio_base64 = await audio_queue.get()
        yield f"data: {audio_base64}\n\n"

