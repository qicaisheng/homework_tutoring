from fastapi import FastAPI, Request, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from spike import service


app = FastAPI()

@app.get("/")
async def get():
    with open('spike/template/index.html', 'r', encoding='utf-8') as file:
        html_content = file.read()
    return HTMLResponse(html_content)


@app.route("/upload_image", methods=["POST"])
async def upload_image(request: Request):
    form = await request.form()
    image = form["image"]
    
    image_id, description = service.upload_image(image)

    return JSONResponse({"imageId": image_id, "description": description})



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            image_id = await websocket.receive_text()
            data = await websocket.receive_bytes()
            await service.process_audio(data, image_id, websocket)
    except WebSocketDisconnect:
        print("WebSocket 连接已断开")
    except Exception as e:
        print(f"WebSocket错误: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
