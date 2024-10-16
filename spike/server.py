import json
import os
from fastapi import FastAPI, Request, UploadFile, File, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
import base64
import uuid

app = FastAPI()
image_storage = {}  # 存储图片 ID 和文件内容

# 主页
@app.get("/")
async def get():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>图片上传与分析</title>
        <style>
            #imagePreview {
                max-width: 300px;
                max-height: 300px;
                margin-top: 10px;
            }
            #recordButton {
                width: 100px;
                height: 100px;
                border-radius: 50%;
                background-color: #f0f0f0;
                display: none;
            }
        </style>
    </head>
    <body>
        <h1>上传图片</h1>
        <input type="file" id="imageInput" accept="image/*" />
        <button onclick="uploadImage()">上传图片</button>
        <div id="imageUploadResult"></div>
        <img id="imagePreview" style="display: none;" />
        <h2>录音功能</h2>
        <p>上传图片后，按住按钮开始录音，松开按钮结束录音。</p>
        <button id="recordButton" disabled>按住录音</button>
        <input type="hidden" id="imageIdInput" />
        <div id="recordingStatus"></div>
        <script>
            let mediaRecorder;
            let audioChunks = [];
            let isRecording = false;

            function uploadImage() {
                const input = document.getElementById("imageInput");
                const file = input.files[0];
                if (!file) {
                    alert("请选择一张图片");
                    return;
                }
                const formData = new FormData();
                formData.append("image", file);
                
                fetch("/upload_image", {
                    method: "POST",
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById("imageUploadResult").innerHTML = "图片上传成功！图片ID: " + data.imageId + "<br>题目描述: " + data.description;
                    document.getElementById("imageIdInput").value = data.imageId;
                    document.getElementById("recordButton").style.display = "block";
                    document.getElementById("recordButton").disabled = false;
                    
                    // 显示图片预览
                    const preview = document.getElementById("imagePreview");
                    preview.src = URL.createObjectURL(file);
                    preview.style.display = "block";
                })
                .catch(error => {
                    console.error("上传图片时出错:", error);
                    document.getElementById("imageUploadResult").innerHTML = "上传图片失败，请重试。";
                });
            }

            async function startRecording() {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    sendAudioToServer(audioBlob);
                };

                mediaRecorder.start();
                isRecording = true;
                document.getElementById("recordingStatus").innerText = "正在录音...";
            }

            function stopRecording() {
                if (isRecording) {
                    mediaRecorder.stop();
                    isRecording = false;
                    document.getElementById("recordingStatus").innerText = "录音已结束，正在处理...";
                }
            }

            function sendAudioToServer(audioBlob) {
                const imageId = document.getElementById("imageIdInput").value;
                const reader = new FileReader();
                reader.readAsDataURL(audioBlob);
                reader.onloadend = function() {
                    const base64Audio = reader.result.split(',')[1];
                    const data = JSON.stringify({
                        imageId: imageId,
                        audioData: base64Audio
                    });

                    fetch('/process_audio', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: data
                    })
                    .then(response => response.json())
                    .then(result => {
                        document.getElementById("recordingStatus").innerText = "音频处理结果: " + result.message;
                    })
                    .catch(error => {
                        console.error('音频处理错误:', error);
                        document.getElementById("recordingStatus").innerText = "音频处理失败，请重试。";
                    });
                };
            }

            document.getElementById('recordButton').addEventListener('mousedown', startRecording);
            document.getElementById('recordButton').addEventListener('mouseup', stopRecording);
            document.getElementById('recordButton').addEventListener('mouseleave', stopRecording);
        </script>
    </body>
    </html>
    """)
# 导入所需的模块
from image_analysis import analyze_image
import uuid

# 存储图片ID和题目描述的映射关系
image_description_map = {}

# 修改uploadImage函数
@app.route("/upload_image", methods=["POST"])
async def upload_image(request: Request):
    form = await request.form()
    image = form["image"]
    
    # 生成唯一的图片ID
    image_id = str(uuid.uuid4())
    
    # 保存图片到临时文件
    temp_image_path = f"temp_{image_id}.jpg"
    with open(temp_image_path, "wb") as f:
        f.write(image.file.read())
    
    # 分析图片获取题目描述
    description = analyze_image(temp_image_path)
    
    # 建立图片ID和题目描述的映射关系
    image_description_map[image_id] = description
    
    # 删除临时文件
    os.remove(temp_image_path)
    
    return JSONResponse({"imageId": image_id, "description": description})

# 添加处理音频的路由
@app.post("/process_audio")
async def process_audio(request: Request):
    data = await request.json()
    image_id = data["imageId"]
    audio_data = data["audioData"]

    # 解码base64音频数据
    audio_bytes = base64.b64decode(audio_data)

    # 生成唯一的音频文件名
    audio_filename = f"audio_{uuid.uuid4()}.wav"

    # 保存音频文件
    with open(audio_filename, "wb") as audio_file:
        audio_file.write(audio_bytes)

    # 这里可以添加音频处理逻辑
    # 例如：调用语音识别API，分析音频内容等

    # 获取对应的图片描述
    description = image_description_map.get(image_id, "未找到对应的图片描述")

    # 这里应该添加实际的音频处理逻辑
    # 暂时返回一个示例消息
    message = f"音频已处理。图片描述：{description}"

    # 删除临时音频文件
    os.remove(audio_filename)

    return JSONResponse({"message": message})

# WebSocket 处理
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        payload = json.loads(data)

        image_id = payload["imageId"]
        audio_data = payload["audioData"]

        # 这里进行音频处理（假设返回与图像相关的音频）
        # 这里的示例代码直接将音频数据返回，可以替换为实际的音频生成逻辑
        if image_id in image_storage:
            # 在这里你可以根据 image_id 处理 audio_data
            generated_audio = audio_data  # 直接返回接收到的音频数据
            await websocket.send_text(generated_audio)
        else:
            await websocket.send_text("Invalid image ID.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)