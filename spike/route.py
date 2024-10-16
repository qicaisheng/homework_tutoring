import json
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from spike import service

app = FastAPI()
image_storage = {}  # 存储图片 ID 和文件内容

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
                # display: none;
                display: block;
            }
            .loading {
                display: none;
                margin-top: 10px;
            }
        </style>
    </head>
    <body>
        <h1>上传图片</h1>
        <input type="file" id="imageInput" accept="image/*" />
        <button onclick="uploadImage()">上传图片</button>
        <div id="loading" class="loading">正在上传和处理图片...</div>
        <div id="imageUploadResult"></div>
        <img id="imagePreview" style="display: none;" />
        <h2>录音功能</h2>
        <p>上传图片后，按住按钮开始录音，松开按钮结束录音。</p>
        <button id="recordButton" >按住录音</button>
        # <input  id="imageIdInput" value="2890e8fc-66b0-4404-9b00-ffae791be000" />
        <div id="recordingStatus"></div>
        <div id="audioPlayback"></div>
        <script>
            let mediaRecorder;
            let audioChunks = [];
            let isRecording = false;
            let debounceTimer;
            let eventSource;

            function uploadImage() {
                const input = document.getElementById("imageInput");
                const file = input.files[0];
                if (!file) {
                    alert("请选择一张图片");
                    return;
                }
                const formData = new FormData();
                formData.append("image", file);
                
                // 显示加载提示
                document.getElementById("loading").style.display = "block";
                document.getElementById("imageUploadResult").innerHTML = "";
                
                fetch("/upload_image", {
                    method: "POST",
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    // 隐藏加载提示
                    document.getElementById("loading").style.display = "none";
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
                    document.getElementById("loading").style.display = "none";
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
                    const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
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
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
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
                            startAudioStream();
                        })
                        .catch(error => {
                            console.error('音频处理错误:', error);
                            document.getElementById("recordingStatus").innerText = "音频处理失败，请重试。";
                        });
                    };
                }, 300); // 300毫秒的防抖延迟
            }

            function startAudioStream() {
                if (eventSource) {
                    eventSource.close();
                }
                eventSource = new EventSource('/audio_stream');
                eventSource.onmessage = function(event) {
                    const audioBase64 = event.data;
                    playAudio(audioBase64);
                };
                eventSource.onerror = function(error) {
                    console.error('SSE错误:', error);
                    eventSource.close();
                };
            }

            function playAudio(audioBase64) {
                const audio = new Audio(audioBase64);
                audio.play().catch(e => console.error('音频播放失败:', e));
                document.getElementById("audioPlayback").innerHTML = "正在播放音频...";
            }

            document.getElementById('recordButton').addEventListener('mousedown', startRecording);
            document.getElementById('recordButton').addEventListener('mouseup', stopRecording);
            document.getElementById('recordButton').addEventListener('mouseleave', stopRecording);
        </script>
    </body>
    </html>
    """)


@app.route("/upload_image", methods=["POST"])
async def upload_image(request: Request):
    form = await request.form()
    image = form["image"]
    
    image_id, description = service.upload_image(image)

    return JSONResponse({"imageId": image_id, "description": description})

# 添加处理音频的路由
@app.post("/process_audio")
async def process_audio(request: Request):
    data = await request.json()
    image_id = data["imageId"]
    audio_data = data["audioData"]

    try:
        await service.process_audio(audio_data, image_id)
        return JSONResponse({"status": "success", "message": "音频处理成功"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"音频处理失败: {str(e)}"}, status_code=500)

@app.get("/audio_stream")
async def audio_stream():
    return StreamingResponse(service.generate_audio_stream(), media_type='text/event-stream')


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
