import asyncio
import base64
import os
import uuid
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
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
    audio_filename = f"./audio/audio_{uuid.uuid4()}.wav"

    audio_bytes = base64.b64decode(audio_data)
    with open(audio_filename, "wb") as audio_file:
        audio_file.write(audio_bytes)

    # save_audio_with_pydub(audio_filename, audio_bytes)

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

async def generate_audio_stream():
    while True:
        audio_base64 = await audio_queue.get()
        yield f"data: {audio_base64}\n\n"


def save_audio_with_pydub(file_name, audio_data):
    try:
        # Create an AudioSegment from raw data
        audio_segment = AudioSegment(
            data=audio_data,
            sample_width=4,
            frame_rate=48000,
            channels=1
        )

        # Export the AudioSegment to a WAV file
        audio_segment.export(file_name, format="wav")
        print(f"Audio saved successfully with pydub as {file_name}")

    except CouldntDecodeError:
        print(f"Could not decode audio data for {file_name}")
