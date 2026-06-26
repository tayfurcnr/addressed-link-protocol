from __future__ import annotations

from pathlib import Path
import re


PROTO_DIR = Path(__file__).resolve().parent.parent / "proto"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "alpcom" / "message_registry.py"
PY_ENUM_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "alpcom" / "message_ids.py"
C_ENUM_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "alpcom" / "alp_message_ids.h"

MSG_ID_RE = re.compile(r"^\s*//\s*ALP_MSG_ID:\s*(0x[0-9A-Fa-f]+|\d+)\s*$")
MESSAGE_RE = re.compile(r"^\s*message\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")


def collect_message_mappings() -> list[tuple[int, str, str]]:
    mappings: list[tuple[int, str, str]] = []
    seen_msg_ids: dict[int, tuple[Path, str]] = {}

    for proto_path in sorted(PROTO_DIR.glob("*.proto")):
        pending_msg_id: int | None = None

        for line_number, line in enumerate(proto_path.read_text(encoding="utf-8").splitlines(), start=1):
            msg_id_match = MSG_ID_RE.match(line)
            if msg_id_match:
                pending_msg_id = int(msg_id_match.group(1), 0)
                if not 0 <= pending_msg_id <= 0xFFFF:
                    raise ValueError(
                        f"{proto_path}:{line_number}: ALP_MSG_ID {pending_msg_id} is out of range; expected 0..65535"
                    )
                continue

            message_match = MESSAGE_RE.match(line)
            if not message_match:
                continue

            if pending_msg_id is None:
                continue

            message_name = message_match.group(1)
            module_name = f"{proto_path.stem}_pb2"
            previous = seen_msg_ids.get(pending_msg_id)
            if previous is not None:
                previous_path, previous_name = previous
                raise ValueError(
                    f"duplicate ALP_MSG_ID 0x{pending_msg_id:04X}: "
                    f"{previous_name} in {previous_path} and {message_name} in {proto_path}"
                )

            seen_msg_ids[pending_msg_id] = (proto_path, message_name)
            mappings.append((pending_msg_id, module_name, message_name))
            pending_msg_id = None

    return mappings


def build_registry_module(mappings: list[tuple[int, str, str]]) -> str:
    import_lines = []
    registry_lines = []

    for msg_id, module_name, message_name in mappings:
        import_lines.append(f"from generated.python.{module_name} import {message_name}")
        registry_lines.append(f"    0x{msg_id:04X}: {message_name},")

    imports = "\n".join(import_lines) if import_lines else ""
    registry_body = "\n".join(registry_lines) if registry_lines else ""

    return "\n".join(
        [
            '"""Auto-generated ALP message registry."""',
            "",
            "from __future__ import annotations",
            "",
            "from alpcom.protocol import CommunicationPacket",
            "from google.protobuf.message import Message",
            imports,
            "",
            "MESSAGE_TYPES = {",
            registry_body,
            "}",
            "",
            "def get_message_type(msg_id: int):",
            "    return MESSAGE_TYPES.get(msg_id)",
            "",
            "def decode_packet_payload(packet: CommunicationPacket) -> Message | None:",
            "    message_type = get_message_type(packet.msg_id)",
            "    if message_type is None:",
            "        return None",
            "",
            "    message = message_type()",
            "    message.ParseFromString(packet.payload)",
            "    return message",
            "",
        ]
    )


def build_python_enum_module(mappings: list[tuple[int, str, str]]) -> str:
    enum_lines = [
        '"""Auto-generated ALP message ID enum."""',
        "",
        "from enum import IntEnum",
        "",
        "",
        "class ALPMessageID(IntEnum):",
    ]

    if mappings:
        for msg_id, _, message_name in mappings:
            enum_lines.append(f"    {message_name.upper()} = 0x{msg_id:04X}")
    else:
        enum_lines.append("    NONE = 0x00")

    enum_lines.extend(
        [
            "",
            "MESSAGE_NAMES = {",
        ]
    )

    for msg_id, _, message_name in mappings:
        enum_lines.append(f'    0x{msg_id:04X}: "{message_name}",')

    enum_lines.append("}")
    enum_lines.append("")
    return "\n".join(enum_lines)


def build_c_enum_header(mappings: list[tuple[int, str, str]]) -> str:
    lines = [
        "#ifndef ALP_MESSAGE_IDS_H",
        "#define ALP_MESSAGE_IDS_H",
        "",
        "typedef enum {",
    ]

    if mappings:
        for msg_id, _, message_name in mappings:
            lines.append(f"    ALP_MSG_{message_name.upper()} = 0x{msg_id:04X},")
    else:
        lines.append("    ALP_MSG_NONE = 0x00,")

    lines.extend(
        [
            "} alp_message_id_t;",
            "",
            "#endif",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    mappings = collect_message_mappings()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_registry_module(mappings), encoding="utf-8")
    PY_ENUM_OUTPUT_PATH.write_text(build_python_enum_module(mappings), encoding="utf-8")
    C_ENUM_OUTPUT_PATH.write_text(build_c_enum_header(mappings), encoding="utf-8")
    print(f"ALP message registry generated: {OUTPUT_PATH}")
    print(f"ALP message ID enum generated: {PY_ENUM_OUTPUT_PATH}")
    print(f"ALP C message ID header generated: {C_ENUM_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
