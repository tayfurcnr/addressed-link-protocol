"""Auto-generated ALP message registry."""

from __future__ import annotations

from alpcom.protocol import CommunicationPacket
from google.protobuf.message import Message
from generated.python.example_pb2 import ExamplePayload

MESSAGE_TYPES = {
    0x40: ExamplePayload,
}

def get_message_type(msg_id: int):
    return MESSAGE_TYPES.get(msg_id)

def decode_packet_payload(packet: CommunicationPacket) -> Message | None:
    message_type = get_message_type(packet.msg_id)
    if message_type is None:
        return None

    message = message_type()
    message.ParseFromString(packet.payload)
    return message
