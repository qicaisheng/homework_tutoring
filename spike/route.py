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
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>作业辅导陪伴助手</title>
        <script src="https://cdn.jsdelivr.net/npm/@gradio/client"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                line-height: 1.6;
            }
            h1, h2 {
                color: #333;
            }
            #imageUploadArea {
                width: 100%;
                height: 300px;
                border: 2px dashed #ccc;
                border-radius: 5px;
                display: flex;
                justify-content: center;
                align-items: center;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            #imageUploadArea:hover {
                border-color: #2196F3;
            }
            #imageUploadArea.dragover {
                background-color: #e3f2fd;
            }
            #imagePreview {
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                margin: auto;
            }
            #uploadText {
                position: absolute;
                z-index: 1;
                text-align: center;
            }
            #confirmUpload {
                display: none;
                margin-top: 10px;
                width: 100%;
                padding: 15px;
                font-size: 18px;
                transition: background-color 0.3s, opacity 0.3s;
            }
            #confirmUpload:hover:not(:disabled) {
                background-color: #1976D2;
            }
            #confirmUpload:disabled {
                background-color: #cccccc;
                cursor: not-allowed;
                opacity: 0.7;
            }
            #recordButton {
                width: 80px;
                height: 80px;
                border-radius: 50%;
                background-color: #2196F3;
                color: white;
                border: none;
                font-size: 16px;
                cursor: pointer;
                transition: background-color 0.3s;
                display: block;
                margin: 20px auto;
            }
            #recordButton:active {
                background-color: #FF0000;
            }
            .loading, #imageUploadResult, #recordingStatus, #audioPlayback {
                margin-top: 10px;
            }
            button {
                margin-top: 10px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .loading-spinner {
                display: inline-block;
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-right: 10px;
            }
            #loading, #audioProcessing {
                text-align: center;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            #voiceInteraction {
                display: none;
                text-align: center;
            }
            #audioPlayback audio {
                width: 100%;
                margin-top: 10px;
            }
            #audioPlaybackError {
                color: red;
                margin-top: 10px;
                display: none;
            }
        </style>
    </head>
    <body>
        <h1>作业辅导陪伴助手</h1>
        <div id="imageUploadArea">
            <p id="uploadText">上传作业图片</p>
            <img id="imagePreview" style="display: none;" alt="预览图片" />
        </div>
        <button id="confirmUpload" style="background-color: #2196F3; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">确认上传</button>
        <div id="loading" class="loading" style="display: none;">
            <div class="loading-spinner"></div>
            <span>正在上传和识别图片...</span>
        </div>
        
        <div id="voiceInteraction" style="display: none;">
            <p>图片识别成功，按住按钮开始对话</p>
            <button id="recordButton">按住对话</button>
            <input type="hidden" id="imageIdInput" />
            <div id="recordingStatus"></div>
            <div id="audioProcessing" style="display: none;">
                <div class="loading-spinner"></div>
                <span>思考中...</span>
            </div>
            <div id="audioPlayback"></div>
            <div id="audioPlaybackError"></div>
        </div>

        <script>
            let mediaRecorder;
            let audioChunks = [];
            let isRecording = false;
            let debounceTimer;
            let eventSource;
            let selectedFile;

            const imageUploadArea = document.getElementById('imageUploadArea');
            const imagePreview = document.getElementById('imagePreview');
            const uploadText = document.getElementById('uploadText');
            const confirmUploadBtn = document.getElementById('confirmUpload');
            const voiceInteraction = document.getElementById('voiceInteraction');

            imageUploadArea.addEventListener('click', () => {
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = 'image/*';
                input.onchange = (e) => {
                    selectedFile = e.target.files[0];
                    previewImage(selectedFile);
                };
                input.click();
            });

            imageUploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                imageUploadArea.classList.add('dragover');
            });

            imageUploadArea.addEventListener('dragleave', () => {
                imageUploadArea.classList.remove('dragover');
            });

            imageUploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                imageUploadArea.classList.remove('dragover');
                selectedFile = e.dataTransfer.files[0];
                previewImage(selectedFile);
            });

            function previewImage(file) {
                if (!file) {
                    alert("请选择一张图片");
                    return;
                }
                const reader = new FileReader();
                reader.onload = (e) => {
                    imagePreview.src = e.target.result;
                    imagePreview.style.display = 'block';
                    uploadText.style.display = 'none';
                    confirmUploadBtn.style.display = 'block';
                    // 图片变更后，隐藏语音区域并清空imageId
                    voiceInteraction.style.display = 'none';
                    document.getElementById("imageIdInput").value = '';
                };
                reader.readAsDataURL(file);
            }

            let uploadDebounceTimer;
            confirmUploadBtn.addEventListener('click', () => {
                clearTimeout(uploadDebounceTimer);
                uploadDebounceTimer = setTimeout(() => {
                    if (selectedFile) {
                        handleImageUpload(selectedFile);
                    } else {
                        alert("请先选择一张图片");
                    }
                }, 300);
            });

            function handleImageUpload(file) {
                const formData = new FormData();
                formData.append("image", file);
                
                document.getElementById("loading").style.display = "flex";
                confirmUploadBtn.disabled = true;
                
                fetch("/upload_image", {
                    method: "POST",
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById("loading").style.display = "none";
                    document.getElementById("imageIdInput").value = data.imageId;
                    confirmUploadBtn.disabled = false;
                    voiceInteraction.style.display = 'block';
                })
                .catch(error => {
                    console.error("上传图片时出错:", error);
                    document.getElementById("loading").style.display = "none";
                    document.getElementById("imageUploadResult").innerHTML = "上传图片失败，请重试。";
                    confirmUploadBtn.disabled = false;
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
                    document.getElementById("recordingStatus").innerText = "";
                    document.getElementById("audioProcessing").style.display = "flex";
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
                            document.getElementById("audioProcessing").style.display = "none";
                            startAudioStream();
                        })
                        .catch(error => {
                            console.error('音频处理错误:', error);
                            document.getElementById("audioProcessing").style.display = "none";
                            document.getElementById("recordingStatus").innerText = "音频处理失败，请重试。";
                        });
                    };
                }, 300);
            }

            let audioQueue = [];
            let isPlaying = false;

            function startAudioStream() {
                if (eventSource) {
                    eventSource.close();
                }
                eventSource = new EventSource('/audio_stream');
                eventSource.onmessage = function(event) {
                    const audioBase64 = event.data;
                    audioQueue.push(audioBase64);
                    if (!isPlaying) {
                        playNextAudio();
                    }
                };
                eventSource.onerror = function(error) {
                    console.error('SSE错误:', error);
                    eventSource.close();
                };
            }

            function playNextAudio() {
                if (audioQueue.length > 0) {
                    isPlaying = true;
                    const audioBase64 = audioQueue.shift();
                    const audioElement = document.createElement('audio');
                    audioElement.src = audioBase64;
                    audioElement.controls = true;
                    audioElement.onended = function() {
                        isPlaying = false;
                        playNextAudio();
                    };
                    document.getElementById("audioPlayback").innerHTML = '';
                    document.getElementById("audioPlayback").appendChild(audioElement);
                    audioElement.play().catch(e => {
                        console.error('音频播放失败:', e);
                        document.getElementById("audioPlaybackError").innerText = "音频播放失败，请重试。";
                        document.getElementById("audioPlaybackError").style.display = "block";
                        isPlaying = false;
                        playNextAudio();
                    });
                } else {
                    isPlaying = false;
                }
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
        await service.process_audio(audio_data)
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
