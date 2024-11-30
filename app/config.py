from app.service.tts.tts import TTS
from app.service.asr.asr import ASR
from app.core.llm_model import LLM_MODEL
from app.core.language import Language

# host = "10.10.30.164"
host = "localhost"
audio_base_url = f"http://{host}:8082/"
audio_file_direction = "../audio"
udp_host = host
speech_udp_port = 8085
image_udp_port = 8086
mqtt_host = host
mqtt_port = 1883

tts = TTS.VOLCENGINE
asr = ASR.VOLCENGINE
llm = LLM_MODEL.ZHIPU

language = Language.CN

tts_spliter_flag = True