from typing import Annotated

from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.mqtt.manager import mqtt_manager
from app.mqtt.publisher import update_config as mqtt_update_config, UpdateConfigData
from app.mqtt.client import publish as mqtt_publish
import asyncio

from app.system.db import yield_postgresql_session, postgresql_session_context
from app.udp.audio_server import start_audio_udp_server
import app.config as config
import app.service.login_service as login_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print(f"Try to connect and start MQTT client")
        mqtt_manager.connect()
        print(f"Succeed to connect and start MQTT client")

        print(f"Try to start udp server")
        asyncio.create_task(start_audio_udp_server())
        print(f"Succeed to start udp server")

        yield
    except Exception as e:
        print(f"Failed to connect or start MQTT client: {e}")
    finally:
        print(f"Try to disconnect and stop MQTT client")
        mqtt_manager.disconnect()
        print(f"Succeed to disconnect and stop MQTT client")

        global udp_server_running
        udp_server_running = False
        print("Shutting down UDP server...")


app = FastAPI(lifespan=lifespan)


@app.post("/publish/")
async def publish_message(topic: str, message: str):
    result = mqtt_publish(topic, message)
    if result.rc == 0:
        return {"status": "Message published successfully"}
    else:
        return {"status": f"Failed to publish message, return code {result.rc}"}


@app.post("/publish-update-config/")
async def publish_message():
    result = mqtt_update_config(
        UpdateConfigData(speechUdpServerHost=config.udp_host, speechUdpServerPort=config.udp_port))
    if result.rc == 0:
        return {"status": "Message published successfully"}
    else:
        return {"status": f"Failed to publish message, return code {result.rc}"}


class DeviceLoginRequest(BaseModel):
    device_sn: str
    role_code: int


@app.post("/devices/login")
def device_login(request: DeviceLoginRequest, session: Annotated[Session, Depends(yield_postgresql_session)]):
    token = postgresql_session_context.set(session)

    device_sn = request.device_sn
    login_service.device_login(device_sn=device_sn)

    postgresql_session_context.reset(token)
