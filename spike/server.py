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
        <title>音频流式传输</title>
    </head>
    <body>
        <h1>上传图片</h1>
        <input type="file" id="imageInput" accept="image/*" />
        <button onclick="uploadImage()">上传图片</button>
        <div id="imageUploadResult"></div>
        <h2>上传音频并关联图片ID</h2>
        <input type="file" id="audioInput" accept="audio/*" />
        <input type="text" id="imageIdInput" placeholder="图片ID" />
        <button onclick="uploadAudio()">上传音频</button>
        <h2>音频回复</h2>
        <audio id="audioPlayer" controls></audio>
        
        <script>
            const socket = new WebSocket("ws://localhost:8000/ws");

            socket.onmessage = function(event) {
                const audioPlayer = document.getElementById("audioPlayer");
                audioPlayer.src = event.data;
                audioPlayer.play();
            };
                        
            function uploadImage() {
                const input = document.getElementById("imageInput");
                const file = input.files[0];
                const formData = new FormData();
                formData.append("image", file);
                
                fetch("/upload_image", {
                    method: "POST",
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    document.getElementById("imageUploadResult").innerHTML = "图片上传成功！图片ID: " + data.imageId + "<br>题目描述: " + data.description;
                })
                .catch(error => {
                    console.error("上传图片时出错:", error);
                    document.getElementById("imageUploadResult").innerHTML = "上传图片失败，请重试。";
                });
            }

            function uploadAudio() {
                const input = document.getElementById("audioInput");
                const imageId = document.getElementById("imageIdInput").value;
                const file = input.files[0];
                const reader = new FileReader();

                reader.onload = function(event) {
                    const audioData = event.target.result.split(',')[1]; // 获取 Base64 数据
                    const data = {
                        imageId: imageId,
                        audioData: audioData
                    };
                    socket.send(JSON.stringify(data));
                };

                reader.readAsDataURL(file);
            }
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

# 修改前端的uploadImage函数

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
