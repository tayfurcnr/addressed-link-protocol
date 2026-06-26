"""Public Python imports for ALP."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from alpcom.protocol import ALPConfig, ALPStreamParser, CRC16, CommunicationPacket, PacketFlags

try:
    from alpcom.message_registry import MESSAGE_TYPES, decode_packet_payload, get_message_type
except ImportError:  # pragma: no cover - registry may not exist before generation
    MESSAGE_TYPES = {}

    def get_message_type(msg_id: int):
        return MESSAGE_TYPES.get(msg_id)

    def decode_packet_payload(packet: CommunicationPacket):
        return None

try:
    from alpcom.message_ids import ALPMessageID, MESSAGE_NAMES
except ImportError:  # pragma: no cover - enum may not exist before generation
    ALPMessageID = None
    MESSAGE_NAMES = {}

__all__ = [
    "CRC16",
    "ALPConfig",
    "config",
    "CommunicationPacket",
    "PacketFlags",
    "ALPStreamParser",
    "MESSAGE_TYPES",
    "get_message_type",
    "decode_packet_payload",
    "ALPMessageID",
    "MESSAGE_NAMES",
]

try:
    from google.protobuf.message import Message
except ImportError:  # pragma: no cover - protobuf may be optional in some environments
    Message = None


def config(*, src_id: int, version: int = 1, default_flags: int = 0) -> ALPConfig:
    """Short helper for building an ALPConfig instance."""

    return ALPConfig(
        src_id=src_id,
        version=version,
        default_flags=default_flags,
    )


def _load_generated_messages() -> None:
    if Message is None:
        return

    generated_dir = Path(__file__).resolve().parent.parent / "generated" / "python"
    for module_path in sorted(generated_dir.glob("*_pb2.py")):
        module = import_module(f"generated.python.{module_path.stem}")
        for name, value in vars(module).items():
            if isinstance(value, type) and issubclass(value, Message) and value is not Message:
                globals()[name] = value
                if name not in __all__:
                    __all__.append(name)


_load_generated_messages()
