import asyncio
import os
import socket
import uuid
from sqlalchemy.orm import Session

import app.config as config
from app.core.token import get_user_by_token
from app.core.user import set_current_user
from app.system.db import yield_postgresql_session, postgresql_session_context

MIDDLE_FRAME_FLAG = b'\x01'
START_FLAG = b'\x02'
END_FLAG = b'\x03'

udp_server_running = True
validated_tokens = {}


async def start_image_udp_server(host='0.0.0.0', port=config.image_udp_port):
    global udp_server_running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"Listening for UDP packets on {host}:{port}")

    current_image = {}
    while udp_server_running:
        data, addr = await asyncio.get_event_loop().run_in_executor(None, sock.recvfrom, 1043)
        if len(data) < 19:
            print(f"Received unexpected packet from {addr}")
            continue

        token = data[:16]
        image_id = data[16:18]
        frame_type = data[18:19]
        payload = data[19:]
        token_hex = token.hex()
        print(f"Received token: {token_hex} ImageId: {image_id}")
        print(f"Received frame type: {frame_type}")

        if frame_type == START_FLAG:
            if token_hex not in validated_tokens:
                _current_user = get_user_by_token(token_hex)
                if not _current_user:
                    print(f"Invalid token received: {token_hex} from {addr}")
                    continue
                validated_tokens[token_hex] = True
                set_current_user(_current_user)
            print(f"Start receiving from {addr}")

        elif frame_type == END_FLAG:
            if token_hex in validated_tokens:
                if payload:
                    print(payload)
                    print(f"Unexpected payload in end frame from {addr}")
                if current_image.get(token_hex):
                    file_id = str(uuid.uuid4())
                    directory = config.image_file_direction
                    file_path = f"{directory}/image-{file_id}.jpg"

                    if not os.path.exists(directory):
                        os.makedirs(directory)
                    # save_image()
                    print(f"Image saved as {file_path}")
                    session: Session = next(yield_postgresql_session())
                    pg_context_token = postgresql_session_context.set(session)
                    try:
                        # await save_image(file_path, image_id)
                        pass
                    finally:
                        session.close()
                        postgresql_session_context.reset(pg_context_token)

                    del validated_tokens[token_hex]
                    del current_image[token_hex]
            else:
                print(f"Invalid token, ignoring end frame from {addr}")

        elif frame_type == MIDDLE_FRAME_FLAG:
            if validated_tokens.get(token_hex):
                current_image[token_hex] = current_image.get(token_hex, b'') + payload
                print(f"Received {len(payload)} bytes from {addr}")
            else:
                print(f"Invalid token, ignoring data from {addr}")
        else:
            print(f"Unknown frame type: {frame_type} from {addr}")

    sock.close()
    print("UDP server closed")

