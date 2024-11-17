from fastapi import FastAPI, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from spike import service


app = FastAPI()

@app.get("/ai/")
async def index():
    with open('spike/template/index.html', 'r', encoding='utf-8') as file:
        html_content = file.read()
    return HTMLResponse(html_content)


@app.get("/ai/homework_tutoring")
async def get():
    with open('spike/template/homework_tutoring.html', 'r', encoding='utf-8') as file:
        html_content = file.read()
    return HTMLResponse(html_content)


@app.post("/ai/upload_image")
async def upload_image(request: Request):
    form = await request.form()
    image = form["image"]
    user_id = form["user_id"]
    
    image_id = await service.upload_image(image)

    return JSONResponse({"imageId": image_id})


@app.websocket("/ai/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    while True:
        try:
            json = await websocket.receive_json()
            image_id = json["image_id"]
            user_id = json["user_id"]
            audio = await websocket.receive_bytes()

            await service.process_audio(audio, user_id, image_id, websocket)
        except Exception as e:
            print(f"WebSocket 处理时发生错误: {e}")
            break  # 


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
