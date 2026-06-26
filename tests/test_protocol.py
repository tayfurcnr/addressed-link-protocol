import unittest

from alpcom.protocol import ALPStreamParser, CommunicationPacket


class ALPStreamParserTests(unittest.TestCase):
    @staticmethod
    def make_packet(*, msg_id: int, seq: int, payload: bytes) -> CommunicationPacket:
        return CommunicationPacket(
            version=2,
            src_id=0x1201,
            dst_id=0x3402,
            msg_id=msg_id,
            seq=seq,
            payload=payload,
        )

    def test_split_sof_across_appends_is_preserved(self) -> None:
        packet = self.make_packet(msg_id=0x31, seq=0x05, payload=b"abc")
        raw = packet.serialize()
        parser = ALPStreamParser()

        self.assertEqual(parser.append(raw[:1]), [])

        packets = parser.append(raw[1:])

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].serialize(), raw)

    def test_invalid_prefix_before_split_sof_is_discarded(self) -> None:
        packet = CommunicationPacket(
            version=2,
            src_id=0x0102,
            dst_id=0x0304,
            msg_id=0x05,
            seq=0x06,
            payload=b"payload",
        )
        raw = packet.serialize()
        parser = ALPStreamParser()

        self.assertEqual(parser.append(b"\x00\x11\xAA"), [])

        packets = parser.append(raw[1:])

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].serialize(), raw)

    def test_crc_mismatch_raises(self) -> None:
        packet = self.make_packet(msg_id=0x31, seq=0x05, payload=b"abc")
        raw = bytearray(packet.serialize())
        raw[-1] ^= 0x01

        with self.assertRaises(ValueError):
            CommunicationPacket.deserialize(bytes(raw))

    def test_uint16_msg_id_round_trips(self) -> None:
        packet = self.make_packet(msg_id=0x1234, seq=0x05, payload=b"abc")

        parsed = CommunicationPacket.deserialize(packet.serialize())

        self.assertEqual(parsed.msg_id, 0x1234)

    def test_multi_packet_stream_returns_both_packets(self) -> None:
        packet_a = self.make_packet(msg_id=0x0101, seq=0x01, payload=b"A")
        packet_b = self.make_packet(msg_id=0x0102, seq=0x02, payload=b"BC")
        parser = ALPStreamParser()

        packets = parser.append(packet_a.serialize() + packet_b.serialize())

        self.assertEqual([packet.msg_id for packet in packets], [0x0101, 0x0102])
        self.assertEqual([packet.payload for packet in packets], [b"A", b"BC"])

    def test_truncated_frame_waits_for_remainder(self) -> None:
        packet = self.make_packet(msg_id=0x0201, seq=0x09, payload=b"hello")
        raw = packet.serialize()
        parser = ALPStreamParser()

        self.assertEqual(parser.append(raw[:-2]), [])

        packets = parser.append(raw[-2:])

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].serialize(), raw)

    def test_garbage_and_corrupt_frame_before_valid_frame_recovers(self) -> None:
        corrupt = bytearray(self.make_packet(msg_id=0x0301, seq=0x01, payload=b"bad").serialize())
        corrupt[-1] ^= 0x01
        valid = self.make_packet(msg_id=0x0302, seq=0x02, payload=b"good").serialize()
        parser = ALPStreamParser()

        packets = parser.append(b"\x99\x88" + bytes(corrupt) + valid)

        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0].msg_id, 0x0302)
        self.assertEqual(packets[0].payload, b"good")

    def test_invalid_size_field_raises(self) -> None:
        raw = bytearray(self.make_packet(msg_id=0x0401, seq=0x03, payload=b"abc").serialize())
        raw[11] = 0x00
        raw[12] = 0x02

        with self.assertRaises(ValueError):
            CommunicationPacket.deserialize(bytes(raw))


if __name__ == "__main__":
    unittest.main()
