from app.utils.uuid_util import get_uuid4_no_hyphen
import app.mqtt.publisher as mqtt_publisher
import app.config as config


def device_login(device_sn: str):
    token = get_uuid4_no_hyphen()
    data = mqtt_publisher.UpdateTokenData(token=token)
    mqtt_publisher.update_token(data=data, device_sn=device_sn)
    data = mqtt_publisher.UpdateConfigData(speechUdpServerHost=config.udp_host, speechUdpServerPort=config.udp_port)
    mqtt_publisher.update_config(data=data, device_sn=device_sn)
    self_introduction_voice = f"https://ark.cn-beijing.volces.com/api/v3/voice/self_introduction/"
    data = mqtt_publisher.UpdateStartVoiceData(url=self_introduction_voice, etag="")
    mqtt_publisher.update_start_voice(data=data, device_sn=device_sn)
