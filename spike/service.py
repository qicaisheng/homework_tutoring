import base64
import os
import uuid

from spike.image_analysis import analyze_image

image_description_map = {}

def upload_image(image):
    image_id = str(uuid.uuid4())
    
    temp_image_path = f"temp_{image_id}.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(image.file.read())
    
    description = analyze_image(temp_image_path)
    
    image_description_map[image_id] = description
    
    os.remove(temp_image_path)

    return image_id, description


def process_audio(audio_data, image_id):
    audio_filename = f"./audio/audio_{uuid.uuid4()}.wav"

    audio_bytes = base64.b64decode(audio_data)

    with open(audio_filename, "wb") as audio_file:
        audio_file.write(audio_bytes)

