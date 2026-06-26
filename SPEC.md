# ALP Protocol Specification

Version: draft for current repository implementation

`ALP` stands for `Addressed Link Protocol`.

This document defines the on-wire frame format and behavioral rules implemented by this repository. It is intended to be the protocol reference for Python, C, and embedded integrations.

## 1. Scope

ALP is a compact binary framing protocol for addressed message exchange over byte streams such as serial links, UART bridges, TCP streams, radio modems, or similar transports.

ALP provides:

- frame boundary detection
- source and destination addressing
- per-frame message typing
- sequence numbering
- flag bits
- payload length declaration
- CRC16 integrity protection

ALP does not define:

- transport discovery
- session establishment
- retransmission policy
- encryption format
- compression format
- message schema format beyond carrying opaque payload bytes

## 2. Conformance Language

The key words `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, and `MAY` in this document are to be interpreted as normative requirements.

## 3. Frame Format

Each ALP frame uses the following binary layout:

```text
SOF1 | SOF2 | VERSION | SRC_ID | DST_ID | MSG_ID | SEQ | FLAGS | PAYLOAD_LENGTH | PAYLOAD | CRC16
```

Field widths in bytes:

```text
1    |  1   |    1    |   2    |   2    |   2    |  1  |   1   |       2        |   N     |   2
```

Total frame size:

```text
13-byte header + N-byte payload + 2-byte CRC
```

The minimum valid frame size is `15` bytes.

## 4. Byte Order

All multi-byte integer fields in ALP MUST use big-endian byte order.

This applies to:

- `SRC_ID`
- `DST_ID`
- `PAYLOAD_LENGTH`
- `CRC16`

## 5. Field Definitions

### 5.1 SOF1

- Size: `1 byte`
- Value: `0xAA`

This is the first start-of-frame marker byte.

### 5.2 SOF2

- Size: `1 byte`
- Value: `0x55`

This is the second start-of-frame marker byte.

The start-of-frame sequence is therefore:

```text
AA 55
```

### 5.3 VERSION

- Size: `1 byte`
- Range: `0x00..0xFF`

This field identifies the ALP wire-format version used by the sender.

Current repository examples use `VERSION = 2`.

### 5.4 SRC_ID

- Size: `2 bytes`
- Range: `0x0000..0xFFFF`

This field identifies the sender address.

### 5.5 DST_ID

- Size: `2 bytes`
- Range: `0x0000..0xFFFF`

This field identifies the destination address.

Reserved value:

- `0xFFFF` = broadcast destination

Frames with `DST_ID = 0xFFFF` are broadcast frames.

### 5.6 MSG_ID

- Size: `2 bytes`
- Range: `0x0000..0xFFFF`

This field identifies the payload message type or application-level command.

When using the repository's protobuf generation flow, each message type MAY declare a message ID with:

```text
// ALP_MSG_ID: 0x0040
```

The declared value MUST fit in two bytes. Values outside `0..65535` are invalid.

Each declared `MSG_ID` SHOULD be unique within a protocol family. The repository generator rejects duplicate IDs.

### 5.7 SEQ

- Size: `1 byte`
- Range: `0x00..0xFF`

This field carries an application-defined sequence value.

ALP itself does not define wrap handling, retransmission semantics, or acknowledgment pairing. Those are left to higher-layer policy.

### 5.8 FLAGS

- Size: `1 byte`

Currently defined flags:

- `0x01` = `ACK_REQUIRED`
- `0x02` = `COMPRESSED`
- `0x04` = `ENCRYPTED`
- `0x08` = `RETRY`
- `0x10` = `PRIORITY`

Undefined flag bits are reserved for future use.

Senders SHOULD set undefined bits to `0`.
Receivers MAY ignore unknown bits unless a higher-level profile defines stricter handling.

### 5.9 PAYLOAD_LENGTH

- Size: `2 bytes`
- Range: `0x0000..0xFFFF`

This field gives the number of bytes in `PAYLOAD`.

Maximum payload size is therefore `65535` bytes.

### 5.10 PAYLOAD

- Size: `N bytes`

This field is opaque to ALP itself.

Examples of valid payload content:

- raw binary data
- UTF-8 text
- protobuf-serialized bytes
- application-defined command structures

ALP framing rules do not change based on payload type.

### 5.11 CRC16

- Size: `2 bytes`

This field carries the CRC-CCITT-FALSE result for the bytes covered by the ALP CRC calculation.

## 6. CRC Rules

ALP uses `CRC-CCITT-FALSE` with the following parameters:

```text
Polynomial : 0x1021
Initial    : 0xFFFF
XOR Out    : 0x0000
Reflect In : False
Reflect Out: False
```

CRC coverage MUST be:

```text
VERSION | SRC_ID | DST_ID | MSG_ID | SEQ | FLAGS | PAYLOAD_LENGTH | PAYLOAD
```

The following bytes are NOT included in the CRC input:

- `SOF1`
- `SOF2`
- `CRC16`

The transmitted CRC value MUST be encoded as big-endian.

Note: a computed CRC value of `0x0000` is valid and MUST NOT be treated as an error condition by implementations.

## 7. Frame Validation

A receiver MUST reject a frame if any of the following is true:

- the frame is shorter than 15 bytes
- `SOF1` is not `0xAA`
- `SOF2` is not `0x55`
- the actual byte count does not equal `13 + PAYLOAD_LENGTH + 2`
- the received CRC does not match the computed CRC

If a frame is rejected inside a stream parser, the parser SHOULD attempt resynchronization by searching for the next possible `AA 55` sequence.

## 8. Stream Parsing Behavior

ALP is intended to run over streaming transports. A parser MAY receive frames split across multiple reads.

A conforming stream parser SHOULD:

- buffer partial frames until enough bytes are available
- scan for the `AA 55` start-of-frame sequence
- discard leading garbage bytes before a valid SOF
- preserve a trailing partial SOF prefix across input boundaries

Example:

- chunk 1 ends with `0xAA`
- chunk 2 begins with `0x55`

The parser SHOULD retain the trailing `0xAA` from chunk 1 so the combined `AA 55` SOF is recognized when chunk 2 arrives.

## 9. Addressing Semantics

ALP defines only raw 16-bit source and destination identifiers.

The protocol does not define:

- address leasing
- node discovery
- reserved unicast ranges
- routing

Only one address value is reserved by the base protocol:

- `DST_ID = 0xFFFF` for broadcast

Higher-level deployments MAY define additional address conventions.

## 10. Broadcast Guidance

Broadcast frames use `DST_ID = 0xFFFF`.

Because multiple receivers may observe the same frame, higher-level designs SHOULD use care with `ACK_REQUIRED` on broadcast traffic. The base protocol does not define collision avoidance or coordinated reply behavior.

## 11. Message ID Registry Guidance

The base protocol defines `MSG_ID` as a 16-bit field.

This repository currently supports generated message registries from `.proto` files using `ALP_MSG_ID` annotations. In that flow:

- each annotated message definition maps to exactly one `MSG_ID`
- IDs MUST be in the range `0x0000..0xFFFF`
- duplicate IDs are invalid

Projects building on ALP SHOULD maintain a stable registry of assigned IDs to avoid collisions across firmware and host applications.

## 12. Example Frame

Illustrative layout:

```text
AA 55 02 12 01 34 02 00 31 05 10 00 03 41 42 43 CRC_H CRC_L
```

Decoded:

- `SOF = AA 55`
- `VERSION = 0x02`
- `SRC_ID = 0x1201`
- `DST_ID = 0x3402`
- `MSG_ID = 0x0031`
- `SEQ = 0x05`
- `FLAGS = 0x10`
- `PAYLOAD_LENGTH = 0x0003`
- `PAYLOAD = 41 42 43` (`"ABC"`)
- `CRC16 = computed over VERSION..PAYLOAD`

## 13. Compatibility Notes

This specification reflects the repository's current implementation behavior.

In particular:

- the wire format uses 1-byte `VERSION`, `SEQ`, and `FLAGS`, plus a 2-byte `MSG_ID`
- the payload is length-prefixed with a 2-byte field
- stream parsers are expected to recover from garbage and fragmented SOF sequences

Any future incompatible wire-format change SHOULD use a distinct `VERSION` policy and be documented explicitly.
