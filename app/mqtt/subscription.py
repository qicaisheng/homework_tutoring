import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

import app.mqtt.event as mqtt_event
import app.service.login_service as login_service
from app.system.db import yield_postgresql_session, postgresql_session_context


def processTopic1(client, userdata, msg: mqtt.MQTTMessage):
    print(f"Received on {msg.topic}: {msg.payload.decode()}")


def processEventPost(client, userdata, msg: mqtt.MQTTMessage):
    print(f"Received on {msg.topic}: {msg.payload.decode()}")
    _device_sn = get_device_sn(msg.topic)

    session: Session = next(yield_postgresql_session())
    token = postgresql_session_context.set(session)
    try:
        event: mqtt_event.ReceivedEvent
        try:
            event = mqtt_event.ReceivedEvent.model_validate_json(msg.payload.decode())
        except ValueError as e:
            print(f"Validation error: {e}")
            return
        if mqtt_event.ReceivedIdentifier.LOGIN.value == event.identifier:
            login_service.device_login(device_sn=_device_sn)
    finally:
        postgresql_session_context.reset(token)

def processCommandAck(client, userdata, msg: mqtt.MQTTMessage):
    print(f"Received on {msg.topic}: {msg.payload.decode()}")


def processDataPost(client, userdata, msg: mqtt.MQTTMessage):
    print(f"Received on {msg.topic}: {msg.payload.decode()}")


def get_device_sn(topic: str) -> str:
    try:
        return topic.split('/')[2]
    except IndexError:
        raise ValueError("Invalid topic format")


subscriptions = {
    "test/topic1": processTopic1,

    "/user/+/event": processEventPost,
    "/user/+/data": processDataPost,
    "/user/+/command/callAck": processCommandAck,
}
