import base64
import uuid


def process_audio(audio_data, image_id):
    audio_filename = f"./audio/audio_{uuid.uuid4()}.wav"

    audio_bytes = base64.b64decode(audio_data)

    with open(audio_filename, "wb") as audio_file:
        audio_file.write(audio_bytes)

