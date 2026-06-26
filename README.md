# ALP

`ALP` stands for `Addressed Link Protocol`.

ALP is a compact framed communication protocol designed for multi-device links. It provides explicit source and destination addressing, a deterministic binary frame layout, CRC16 protection, and optional Protobuf-based payload serialization for both Python and C workflows.

## Overview

ALP frame format:

```text
SOF1 | SOF2 | VERSION | SRC_ID | DST_ID | MSG_ID | SEQ | FLAGS | PAYLOAD_LENGTH | PAYLOAD | CRC16
```

Byte layout:

```text
1    |  1   |    1    |   2    |   2    |   1    |  1  |   1   |       2        |   N     |   2
```

Protocol rules:

- `SOF1 = 0xAA`
- `SOF2 = 0x55`
- Multi-byte fields use big-endian byte order
- `DST_ID = 0xFFFF` is reserved for broadcast traffic
- CRC uses `CRC-CCITT-FALSE`
- CRC coverage is:
  `VERSION | SRC_ID | DST_ID | MSG_ID | SEQ | FLAGS | PAYLOAD_LENGTH | PAYLOAD`

CRC parameters:

```text
Polynomial : 0x1021
Initial    : 0xFFFF
XOR Out    : 0x0000
Reflect In : False
Reflect Out: False
```

## Repository Layout

```text
proto/                  Protobuf schema definitions
generated/python/       Generated Python protobuf modules
generated/c/            Generated C protobuf files for nanopb
alpcom/                 Installable Python package for ALP
third_party/nanopb/     Vendored nanopb runtime for C builds
scripts/                Build and generation scripts
communication_protocol.py
alp_stream_parser.h
alp_stream_parser.c
communication_protocol.h
communication_protocol.c
README.md
```

## Implementations

Python implementation:

- File: `communication_protocol.py`
- Supports raw byte payloads and Protobuf-serialized payloads
- Includes serialization, deserialization, CRC verification, broadcast detection, and demo flows
- Includes generic stream parsing through `ALPStreamParser`
- Includes reusable sender configuration through `ALPConfig`
- Public import layer: `alpcom/__init__.py`

C implementation:

- Public header: `communication_protocol.h`
- Stream parser header: `alp_stream_parser.h`
- File: `communication_protocol.c`
- Implements the ALP frame structure and CRC validation logic
- Generic stream parser implementation: `alp_stream_parser.c`
- Prepared for Protobuf payload integration through generated nanopb output
- Umbrella header: `alpcom/alpcom.h`
- Nanopb runtime: `third_party/nanopb/`
- Arduino library wrapper: `src/`

## Protobuf Payloads

ALP treats the `PAYLOAD` field as an opaque byte array. This means payload content can be:

- raw binary data
- UTF-8 encoded text
- Protobuf-serialized message bytes

Example schema:

- Source: `proto/example.proto`
- `MSG_ID` mapping is declared next to the message with `// ALP_MSG_ID: 0x40`

Python generated output:

- `generated/python/example_pb2.py`

C generated output target:

- `generated/c/example.pb.h`
- `generated/c/example.pb.c`
- Runtime dependency: `third_party/nanopb/pb.h`, `pb_common.c`, `pb_encode.c`, ...

## Build

### Python Protobuf Generation

Generate Python bindings with:

```powershell
.\scripts\generate_proto_python.ps1
```

This script uses:

```powershell
python -m grpc_tools.protoc -I proto --python_out=generated/python proto/example.proto
```

After generation, `alpcom` Python exports remain available automatically. New `*_pb2.py` files are discovered dynamically by `alpcom/__init__.py`.
The same step also generates `alpcom/message_registry.py`, which builds the `MSG_ID -> message type` mapping automatically from `.proto` annotations.
It also generates message ID enums:

```text
alpcom/message_ids.py
alpcom/alp_message_ids.h
```

### C Protobuf Generation

C payload generation uses `nanopb`.

If `nanopb_generator.exe` is installed in the active Python environment, the script finds it automatically. You can still override the path manually with `NANOPB_GENERATOR` if needed:

```powershell
$env:NANOPB_GENERATOR="C:\path\to\nanopb_generator.py"
.\scripts\generate_proto_c.ps1
```

Expected output:

```text
generated/c/example.pb.h
generated/c/example.pb.c
```

After generation, the script also refreshes:

```text
alpcom/alpcom.h
```

This umbrella header automatically includes every generated `*.pb.h` file under `generated/c`.

### Generate Everything

```powershell
.\scripts\generate_all_proto.ps1
```

If `nanopb_generator` is available in the active Python environment, the combined script generates both Python and C outputs. Otherwise it skips C generation unless `NANOPB_GENERATOR` is provided explicitly.

## Installation

Editable local install:

```powershell
python -m pip install -e .
```

Regular install from a packaged source later:

```powershell
python -m pip install .
```

After installation, application code can simply use:

```python
import alpcom
```

`communication_protocol.py` is kept as a compatibility shim, but new Python code should import from `alpcom`.

## Usage

### Python Payload Flow

Typical Python flow:

1. Define the payload schema in `.proto`
2. Generate Python classes
3. Create the Protobuf message
4. Serialize it into bytes
5. Place those bytes into ALP `PAYLOAD`
6. Serialize the ALP frame

Recommended user import:

```python
import alpcom
```

Reusable sender configuration:

```python
config = alpcom.config(src_id=0x1201, version=1)
```

Recommended packet builder for structured payloads:

```python
packet = config.pack_message(...)
```

Receive-side parser:

```python
parser = alpcom.ALPStreamParser()
packets = parser.append(incoming_bytes)
```

Automatic payload decode:

```python
decoded = alpcom.decode_packet_payload(packet)
```

If you generate additional `.proto` files later, their Python message classes become importable from `alpcom` without changing application code.
To register a new message type, add an `ALP_MSG_ID` comment above the `message` definition in the `.proto` file and rerun generation.

Example runner:

```powershell
python -m examples.python_example --port COM3 --baudrate 115200 --mode example
```

Serial example notes:

- Install serial support with `python -m pip install -e .[serial]`
- The example builds `ExamplePayload`, wraps it in an ALP frame, and writes it directly to the selected serial port
- `--dst-id` and `--seq` can be changed from the command line

### C Payload Flow

Typical C flow with `nanopb`:

1. Define the payload schema in `.proto`
2. Generate `example.pb.h` and `example.pb.c`
3. Fill the generated message struct
4. Encode it with `pb_encode`
5. Use the encoded byte buffer as the ALP `PAYLOAD`
6. Serialize the final ALP frame

Reusable sender configuration:

```c
alp_config_t config;
alp_config_init(&config, 0x1201, 1, ALP_FLAG_PRIORITY);
```

Recommended C include:

```c
#include "alpcom/alpcom.h"
```

Receive-side parser entry points:

```c
alp_stream_parser_init(...)
alp_stream_parser_append(...)
```

If you generate additional `.proto` files later, rerunning the C generation script refreshes `alpcom/alpcom.h` so the new generated headers are included automatically.

## Arduino / ESP32

This repository can also be used from ESP32 projects that use the Arduino framework.

Arduino library files:

```text
library.properties
src/alpcom.h
src/alpcom.c
src/alp_stream_parser.c
src/pb.h
src/pb_common.c
src/pb_encode.c
src/pb_decode.c
src/example.pb.c
examples/arduino_example/arduino_example.ino
```

How to use:

1. Put the repository under your Arduino `libraries/` folder, or add it to a PlatformIO Arduino project.
2. Run `.\scripts\generate_proto_c.ps1` before building so `generated/c/*.pb.*` and `alpcom/alp_message_ids.h` are up to date.
3. Open `examples/arduino_example/arduino_example.ino`.
4. Build for your ESP32 Arduino board.

What the Arduino example does:

- creates an `alp_ExamplePayload`
- encodes it with nanopb
- wraps it into an ALP frame
- transmits the final bytes with `Serial.write(...)`

## C Testing

The repository now includes a working nanopb-backed C smoke test path.

ALP-only demo:

```powershell
cmd /c 'call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul && cl /nologo /W4 /Fe:communication_protocol_test.exe communication_protocol.c'
.\communication_protocol_test.exe
```

ALP + Protobuf smoke test:

```powershell
cmd /c 'call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul && cl /nologo /W4 /DALP_NO_DEMO_MAIN /I third_party\nanopb /I generated\c /Fe:protobuf_alp_smoketest.exe tests\protobuf_alp_smoketest.c communication_protocol.c generated\c\example.pb.c third_party\nanopb\pb_common.c third_party\nanopb\pb_encode.c'
.\protobuf_alp_smoketest.exe
```

## Notes

- Generated protobuf files are committed so the Python package and C examples work without an extra generation step after clone
- Protobuf bytes do not change the ALP framing rules; they only define the content of `PAYLOAD`
- Broadcast frames should usually avoid `ACK_REQUIRED` unless the higher-level design explicitly handles reply collisions
- Application code should prefer importing from `alpcom` instead of reaching into `generated/python` directly
- Stream parsers are payload-agnostic; they only recover full ALP frames from incoming byte streams
