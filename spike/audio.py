# from pydub import AudioSegment

# # 加载音频文件
# audio = AudioSegment.from_file("./audio/audio_7eb61496-adb7-4db3-b581-41ba95f63158.wav")

# # 获取采样率
# sample_rate = audio.frame_rate
# print(f"Sample Rate: {sample_rate} Hz")

# # 获取采样宽度
# sample_width = audio.sample_width
# print(f"Sample Width: {sample_width} bytes")

# # 获取声道数
# channels = audio.channels
# print(f"Channels: {channels}")


# """
# Sample Rate: 32000 Hz
# Sample Width: 2 bytes
# Channels: 1
# """


import wave

with wave.open('./audio/audio_7eb61496-adb7-4db3-b581-41ba95f63158.wav', 'rb') as wf:
    # 读取数据
    audio_data = wf.readframes(wf.getnframes())