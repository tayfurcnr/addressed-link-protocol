import unittest

from alpcom.protocol import ALPStreamParser, CommunicationPacket


class ALPStreamParserTests(unittest.TestCase):
    def test_split_sof_across_appends_is_preserved(self) -> None:
        packet = CommunicationPacket(
            version=2,
            src_id=0x1201,
            dst_id=0x3402,
            msg_id=0x31,
            seq=0x05,
            payload=b"abc",
        )
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
        packet = CommunicationPacket(
            version=2,
            src_id=0x1201,
            dst_id=0x3402,
            msg_id=0x31,
            seq=0x05,
            payload=b"abc",
        )
        raw = bytearray(packet.serialize())
        raw[-1] ^= 0x01

        with self.assertRaises(ValueError):
            CommunicationPacket.deserialize(bytes(raw))

    def test_uint16_msg_id_round_trips(self) -> None:
        packet = CommunicationPacket(
            version=2,
            src_id=0x1201,
            dst_id=0x3402,
            msg_id=0x1234,
            seq=0x05,
            payload=b"abc",
        )

        parsed = CommunicationPacket.deserialize(packet.serialize())

        self.assertEqual(parsed.msg_id, 0x1234)


if __name__ == "__main__":
    unittest.main()
