import argparse

import alpcom

try:
    import serial
except ImportError:  # pragma: no cover - optional runtime dependency for serial example
    serial = None


CONFIG = alpcom.config(
    src_id=0x1201,
    version=1,
)


def build_example_packet(dst_id: int, seq: int) -> alpcom.CommunicationPacket:
    message = alpcom.ExamplePayload(
        device_index=7,
        value=24.6,
    )

    return CONFIG.pack_message(
        dst_id=dst_id,
        msg_id=int(alpcom.ALPMessageID.EXAMPLEPAYLOAD),
        seq=seq,
        message=message,
        flags=int(alpcom.PacketFlags.PRIORITY),
    )


def open_serial_port(port: str, baudrate: int, timeout: float):
    if serial is None:
        raise RuntimeError(
            "pyserial is not installed. Run 'python -m pip install -e .[serial]' first."
        )

    return serial.Serial(port=port, baudrate=baudrate, timeout=timeout)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an ExamplePayload ALP frame and send it over serial.")
    parser.add_argument("--port", required=True, help="Serial port name, for example COM3 or /dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baudrate")
    parser.add_argument("--timeout", type=float, default=0.2, help="Serial timeout in seconds")
    parser.add_argument("--dst-id", type=lambda value: int(value, 0), default=0x3402, help="Destination device ID")
    parser.add_argument("--seq", type=lambda value: int(value, 0), default=0x01, help="Sequence number")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    packet = build_example_packet(dst_id=args.dst_id & 0xFFFF, seq=args.seq & 0xFF)
    frame = packet.serialize()

    print("Example payload:")
    print("  type         : ExamplePayload")
    print("  device_index : 7")
    print("  value        : 24.6")
    print()
    print("ALP packet:")
    print(f"  src_id       : 0x{packet.src_id:04X}")
    print(f"  dst_id       : 0x{packet.dst_id:04X}")
    print(f"  msg_id       : 0x{packet.msg_id:02X}")
    print(f"  seq          : 0x{packet.seq:02X}")
    print(f"  flags        : 0x{packet.flags:02X}")
    print(f"  payload_len  : {packet.payload_length}")
    print(f"  packet_hex   : {packet.to_hex()}")

    with open_serial_port(args.port, args.baudrate, args.timeout) as serial_port:
        written = serial_port.write(frame)
        serial_port.flush()
        print()
        print("Serial transmit:")
        print(f"  port         : {serial_port.port}")
        print(f"  baudrate     : {serial_port.baudrate}")
        print(f"  tx_bytes     : {written}")


if __name__ == "__main__":
    main()
