"""
ALP (Addressed Link Protocol).

Frame format:
    SOF1 | SOF2 | VERSION | SRC_ID | DST_ID | MSG_ID | SEQ | FLAGS | PAYLOAD_LENGTH | PAYLOAD | CRC16

Byte layout:
    1    |  1   |    1    |   2    |   2    |   2    |  1  |   1   |       2        |   N     |   2

Rules:
    - Multi-byte fields use big-endian order.
    - CRC16 uses CRC-CCITT-FALSE:
        polynomial = 0x1021
        initial    = 0xFFFF
        xor_out    = 0x0000
        reflect_in = False
        reflect_out= False
    - CRC is calculated over all bytes except SOF1, SOF2 and CRC itself:
        VERSION..PAYLOAD
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
import struct

try:
    from google.protobuf.message import Message
except ImportError:  # pragma: no cover - protobuf may be optional in some environments
    Message = None


class CRC16:
    """CRC-CCITT-FALSE helper."""

    POLYNOMIAL = 0x1021
    INITIAL_VALUE = 0xFFFF

    @classmethod
    def calculate(cls, data: bytes, initial_value: int | None = None) -> int:
        crc = cls.INITIAL_VALUE if initial_value is None else (initial_value & 0xFFFF)

        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ cls.POLYNOMIAL) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF

        return crc


class PacketFlags(IntFlag):
    NONE = 0x00
    ACK_REQUIRED = 0x01
    COMPRESSED = 0x02
    ENCRYPTED = 0x04
    RETRY = 0x08
    PRIORITY = 0x10


@dataclass
class ALPConfig:
    """Reusable ALP sender configuration."""

    src_id: int
    version: int = 2
    default_flags: int = 0

    def __post_init__(self) -> None:
        self.src_id &= 0xFFFF
        self.version &= 0xFF
        self.default_flags &= 0xFF

    def create_packet(
        self,
        *,
        dst_id: int,
        msg_id: int,
        seq: int,
        payload: bytes = b"",
        flags: int | None = None,
    ) -> "CommunicationPacket":
        return CommunicationPacket(
            version=self.version,
            src_id=self.src_id,
            dst_id=dst_id,
            msg_id=msg_id,
            seq=seq,
            flags=self.default_flags if flags is None else flags,
            payload=payload,
        )

    def pack_message(
        self,
        *,
        dst_id: int,
        msg_id: int,
        seq: int,
        message: "Message",
        flags: int | None = None,
    ) -> "CommunicationPacket":
        return CommunicationPacket.pack_message(
            version=self.version,
            src_id=self.src_id,
            dst_id=dst_id,
            msg_id=msg_id,
            seq=seq,
            message=message,
            flags=self.default_flags if flags is None else flags,
        )


class ALPStreamParser:
    """Incremental ALP frame parser for byte streams."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def reset(self) -> None:
        self._buffer.clear()

    def _retain_possible_sof_prefix(self) -> None:
        max_prefix = len(CommunicationPacket.SOF) - 1
        keep = 0
        for prefix_length in range(min(len(self._buffer), max_prefix), 0, -1):
            if self._buffer[-prefix_length:] == CommunicationPacket.SOF[:prefix_length]:
                keep = prefix_length
                break

        if keep == 0:
            self._buffer.clear()
        else:
            del self._buffer[:-keep]

    def append(self, data: bytes) -> list["CommunicationPacket"]:
        if not data:
            return []

        self._buffer.extend(data)
        packets: list[CommunicationPacket] = []

        while True:
            sof_index = self._buffer.find(CommunicationPacket.SOF)
            if sof_index < 0:
                self._retain_possible_sof_prefix()
                break

            if sof_index > 0:
                del self._buffer[:sof_index]

            if len(self._buffer) < CommunicationPacket.HEADER_SIZE:
                break

            try:
                _, _, _, _, _, _, _, payload_length = struct.unpack(
                    CommunicationPacket.HEADER_FORMAT,
                    self._buffer[: CommunicationPacket.HEADER_SIZE],
                )
            except struct.error:
                break

            frame_size = CommunicationPacket.HEADER_SIZE + payload_length + CommunicationPacket.CRC_SIZE
            if len(self._buffer) < frame_size:
                break

            frame = bytes(self._buffer[:frame_size])
            try:
                packets.append(CommunicationPacket.deserialize(frame))
                del self._buffer[:frame_size]
            except ValueError:
                del self._buffer[0]

        return packets


@dataclass
class CommunicationPacket:
    """
    Binary packet model.

    Header bytes:
        SOF1(1) + SOF2(1) + VERSION(1) + SRC_ID(2) + DST_ID(2) + MSG_ID(2) + SEQ(1) + FLAGS(1) + PAYLOAD_LENGTH(2)
    """

    version: int
    src_id: int
    dst_id: int
    msg_id: int
    seq: int
    flags: int = 0
    payload: bytes = b""

    SOF = b"\xAA\x55"
    BROADCAST_ID = 0xFFFF
    PROTOCOL_NAME = "Addressed Link Protocol"
    PROTOCOL_SHORT_NAME = "ALP"
    HEADER_FORMAT = "!2sBHHHBBH"
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    CRC_SIZE = 2
    MIN_PACKET_SIZE = HEADER_SIZE + CRC_SIZE
    MAX_PAYLOAD_SIZE = 0xFFFF

    def __post_init__(self) -> None:
        if not isinstance(self.payload, bytes):
            self.payload = bytes(self.payload)

        if len(self.payload) > self.MAX_PAYLOAD_SIZE:
            raise ValueError(f"payload too large: {len(self.payload)} bytes")

        self.version &= 0xFF
        self.src_id &= 0xFFFF
        self.dst_id &= 0xFFFF
        self.msg_id &= 0xFFFF
        self.seq &= 0xFF
        self.flags &= 0xFF

    @property
    def payload_length(self) -> int:
        return len(self.payload)

    def build_header(self) -> bytes:
        return struct.pack(
            self.HEADER_FORMAT,
            self.SOF,
            self.version,
            self.src_id,
            self.dst_id,
            self.msg_id,
            self.seq,
            self.flags,
            self.payload_length,
        )

    def crc_input(self) -> bytes:
        header = self.build_header()
        return header[2:] + self.payload

    def calculate_crc(self) -> int:
        return CRC16.calculate(self.crc_input())

    def serialize(self) -> bytes:
        header = self.build_header()
        crc = self.calculate_crc()
        return header + self.payload + struct.pack("!H", crc)

    @classmethod
    def deserialize(cls, data: bytes) -> "CommunicationPacket":
        if len(data) < cls.MIN_PACKET_SIZE:
            raise ValueError(f"packet too short: {len(data)} bytes")

        sof, version, src_id, dst_id, msg_id, seq, flags, payload_length = struct.unpack(
            cls.HEADER_FORMAT, data[: cls.HEADER_SIZE]
        )

        if sof != cls.SOF:
            raise ValueError(
                f"invalid SOF: {' '.join(f'0x{byte:02X}' for byte in sof)}"
            )

        expected_size = cls.HEADER_SIZE + payload_length + cls.CRC_SIZE
        if len(data) != expected_size:
            raise ValueError(
                f"size mismatch: expected {expected_size} bytes, got {len(data)} bytes"
            )

        payload_start = cls.HEADER_SIZE
        payload_end = payload_start + payload_length
        payload = data[payload_start:payload_end]
        crc_received = struct.unpack("!H", data[payload_end:payload_end + cls.CRC_SIZE])[0]
        crc_calculated = CRC16.calculate(data[2:payload_end])

        if crc_received != crc_calculated:
            raise ValueError(
                f"CRC mismatch: received 0x{crc_received:04X}, calculated 0x{crc_calculated:04X}"
            )

        packet = cls(version, src_id, dst_id, msg_id, seq, flags, payload)
        packet._crc16 = crc_received
        return packet

    def has_flag(self, flag: PacketFlags) -> bool:
        return bool(self.flags & int(flag))

    def add_flags(self, *flags: PacketFlags) -> "CommunicationPacket":
        for flag in flags:
            self.flags |= int(flag)
        return self

    def to_hex(self) -> str:
        return " ".join(f"{byte:02X}" for byte in self.serialize())

    def is_broadcast(self) -> bool:
        return self.dst_id == self.BROADCAST_ID

    @classmethod
    def pack_message(
        cls,
        *,
        version: int,
        src_id: int,
        dst_id: int,
        msg_id: int,
        seq: int,
        message: "Message",
        flags: int = 0,
    ) -> "CommunicationPacket":
        if Message is None:
            raise RuntimeError("google.protobuf is not available")

        if not isinstance(message, Message):
            raise TypeError("message must be a protobuf Message instance")

        return cls(
            version=version,
            src_id=src_id,
            dst_id=dst_id,
            msg_id=msg_id,
            seq=seq,
            flags=flags,
            payload=message.SerializeToString(),
        )


def describe_protocol() -> str:
    return "\n".join(
        [
            f"{CommunicationPacket.PROTOCOL_SHORT_NAME} - {CommunicationPacket.PROTOCOL_NAME}",
            "",
            "Packet layout:",
            "  SOF1           : 1 byte  (0xAA)",
            "  SOF2           : 1 byte  (0x55)",
            "  VERSION        : 1 byte",
            "  SRC_ID         : 2 bytes (big-endian)",
            "  DST_ID         : 2 bytes (big-endian)",
            "  MSG_ID         : 2 bytes (big-endian)",
            "  SEQ            : 1 byte",
            "  FLAGS          : 1 byte",
            "  PAYLOAD_LENGTH : 2 bytes (big-endian)",
            "  PAYLOAD        : N bytes",
            "  CRC16          : 2 bytes (big-endian)",
            "",
            "Reserved IDs:",
            f"  BROADCAST_ID   : 0x{CommunicationPacket.BROADCAST_ID:04X}",
            "",
            "CRC coverage:",
            "  VERSION | SRC_ID | DST_ID | MSG_ID | SEQ | FLAGS | PAYLOAD_LENGTH | PAYLOAD",
            "",
            "CRC parameters:",
            f"  polynomial = 0x{CRC16.POLYNOMIAL:04X}",
            f"  initial    = 0x{CRC16.INITIAL_VALUE:04X}",
            "",
            "Payload options:",
            "  PAYLOAD can carry raw bytes or serialized structured message bytes.",
        ]
    )


def build_demo_packet() -> CommunicationPacket:
    return CommunicationPacket(
        version=2,
        src_id=0x1201,
        dst_id=0x3402,
        msg_id=0x0031,
        seq=0x05,
        flags=int(PacketFlags.ACK_REQUIRED | PacketFlags.PRIORITY),
        payload=b"TEMP=24.6C",
    )


def build_structured_demo_packet() -> CommunicationPacket | None:
    try:
        from generated.python.example_pb2 import ExamplePayload
    except ImportError:
        return None

    message = ExamplePayload(
        device_index=7,
        value=24.6,
    )

    return CommunicationPacket.pack_message(
        version=2,
        src_id=0x1201,
        dst_id=CommunicationPacket.BROADCAST_ID,
        msg_id=0x0040,
        seq=0x06,
        flags=int(PacketFlags.PRIORITY),
        message=message,
    )


def main() -> None:
    print(describe_protocol())
    print()

    packet = build_demo_packet()
    raw = packet.serialize()
    parsed = CommunicationPacket.deserialize(raw)

    print("Demo packet:")
    print(f"  payload          : {packet.payload!r}")
    print(f"  payload_length   : {packet.payload_length}")
    print(f"  crc_input_hex    : {' '.join(f'{b:02X}' for b in packet.crc_input())}")
    print(f"  crc16            : 0x{packet.calculate_crc():04X}")
    print(f"  packet_hex       : {packet.to_hex()}")
    print()
    print("Parsed packet:")
    print(f"  version          : {parsed.version}")
    print(f"  src_id           : 0x{parsed.src_id:04X}")
    print(f"  dst_id           : 0x{parsed.dst_id:04X}")
    print(f"  msg_id           : 0x{parsed.msg_id:04X}")
    print(f"  seq              : 0x{parsed.seq:02X}")
    print(f"  flags            : 0x{parsed.flags:02X}")
    print(f"  is_broadcast     : {parsed.is_broadcast()}")
    print(f"  ack_required     : {parsed.has_flag(PacketFlags.ACK_REQUIRED)}")
    print(f"  priority         : {parsed.has_flag(PacketFlags.PRIORITY)}")

    structured_packet = build_structured_demo_packet()
    if structured_packet is not None:
        print()
        print("Structured payload demo:")
        print(f"  msg_id           : 0x{structured_packet.msg_id:04X}")
        print(f"  dst_id           : 0x{structured_packet.dst_id:04X}")
        print(f"  is_broadcast     : {structured_packet.is_broadcast()}")
        print(f"  payload_length   : {structured_packet.payload_length}")
        print(f"  packet_hex       : {structured_packet.to_hex()}")


__all__ = [
    "ALPConfig",
    "ALPStreamParser",
    "CRC16",
    "CommunicationPacket",
    "PacketFlags",
    "build_demo_packet",
    "build_structured_demo_packet",
    "describe_protocol",
    "main",
]
