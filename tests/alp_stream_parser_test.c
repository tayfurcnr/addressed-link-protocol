#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "../c/include/alp_stream_parser.h"

static int test_split_sof_is_preserved(void) {
    const uint8_t payload[] = {'O', 'K'};
    uint8_t frame[64];
    uint8_t parser_storage[64];
    alp_stream_parser_t parser;
    alp_packet_t *packet = alp_packet_create(2, 0x1201, 0x3402, 0x31, 0x05, 0, payload, sizeof(payload));
    if (packet == NULL) {
        return 1;
    }

    int frame_size = alp_packet_serialize(packet, frame, sizeof(frame));
    alp_packet_destroy(packet);
    if (frame_size <= 0) {
        return 2;
    }

    alp_stream_parser_init(&parser, parser_storage, sizeof(parser_storage));

    alp_packet_t *parsed = NULL;
    if (alp_stream_parser_append(&parser, frame, 1U, &parsed) != 0 || parsed != NULL) {
        return 3;
    }

    if (alp_stream_parser_append(&parser, frame + 1, (size_t)frame_size - 1U, &parsed) != 1) {
        return 4;
    }

    if (parsed == NULL || parsed->payload_length != sizeof(payload) || memcmp(parsed->payload, payload, sizeof(payload)) != 0) {
        alp_packet_destroy(parsed);
        return 5;
    }

    alp_packet_destroy(parsed);
    return 0;
}

static int test_invalid_prefix_before_split_sof_is_discarded(void) {
    const uint8_t noise_and_sof1[] = {0x00, 0x11, ALP_PACKET_SOF1};
    const uint8_t payload[] = {'A'};
    uint8_t frame[64];
    uint8_t parser_storage[64];
    alp_stream_parser_t parser;
    alp_packet_t *packet = alp_packet_create(2, 0x0010, 0x0020, 0x30, 0x01, 0, payload, sizeof(payload));
    if (packet == NULL) {
        return 10;
    }

    int frame_size = alp_packet_serialize(packet, frame, sizeof(frame));
    alp_packet_destroy(packet);
    if (frame_size <= 0) {
        return 11;
    }

    alp_stream_parser_init(&parser, parser_storage, sizeof(parser_storage));

    alp_packet_t *parsed = NULL;
    if (alp_stream_parser_append(&parser, noise_and_sof1, sizeof(noise_and_sof1), &parsed) != 0 || parsed != NULL) {
        return 12;
    }

    if (alp_stream_parser_append(&parser, frame + 1, (size_t)frame_size - 1U, &parsed) != 1) {
        return 13;
    }

    if (parsed == NULL || parsed->payload_length != sizeof(payload) || parsed->payload[0] != payload[0]) {
        alp_packet_destroy(parsed);
        return 14;
    }

    alp_packet_destroy(parsed);
    return 0;
}

static int test_uint16_msg_id_round_trips(void) {
    const uint8_t payload[] = {'I', 'D'};
    uint8_t frame[64];
    alp_packet_t *packet = alp_packet_create(2, 0x1201, 0x3402, 0x1234, 0x07, 0, payload, sizeof(payload));
    if (packet == NULL) {
        return 20;
    }

    int frame_size = alp_packet_serialize(packet, frame, sizeof(frame));
    alp_packet_destroy(packet);
    if (frame_size <= 0) {
        return 21;
    }

    alp_packet_t *parsed = NULL;
    if (alp_packet_deserialize(frame, (size_t)frame_size, &parsed) != 0) {
        return 22;
    }

    if (parsed == NULL || parsed->msg_id != 0x1234) {
        alp_packet_destroy(parsed);
        return 23;
    }

    alp_packet_destroy(parsed);
    return 0;
}

static int test_multiple_frames_are_parsed_sequentially(void) {
    const uint8_t payload_a[] = {'A'};
    const uint8_t payload_b[] = {'B', '2'};
    uint8_t frame_a[64];
    uint8_t frame_b[64];
    uint8_t combined[128];
    uint8_t parser_storage[128];
    alp_stream_parser_t parser;
    alp_packet_t *packet_a = alp_packet_create(2, 0x1001, 0x2001, 0x0101, 0x01, 0, payload_a, sizeof(payload_a));
    alp_packet_t *packet_b = alp_packet_create(2, 0x1001, 0x2001, 0x0102, 0x02, 0, payload_b, sizeof(payload_b));
    if (packet_a == NULL || packet_b == NULL) {
        alp_packet_destroy(packet_a);
        alp_packet_destroy(packet_b);
        return 30;
    }

    int frame_size_a = alp_packet_serialize(packet_a, frame_a, sizeof(frame_a));
    int frame_size_b = alp_packet_serialize(packet_b, frame_b, sizeof(frame_b));
    alp_packet_destroy(packet_a);
    alp_packet_destroy(packet_b);
    if (frame_size_a <= 0 || frame_size_b <= 0) {
        return 31;
    }

    memcpy(combined, frame_a, (size_t)frame_size_a);
    memcpy(combined + frame_size_a, frame_b, (size_t)frame_size_b);
    alp_stream_parser_init(&parser, parser_storage, sizeof(parser_storage));

    alp_packet_t *parsed = NULL;
    if (alp_stream_parser_append(&parser, combined, (size_t)(frame_size_a + frame_size_b), &parsed) != 1) {
        return 32;
    }
    if (parsed == NULL || parsed->msg_id != 0x0101) {
        alp_packet_destroy(parsed);
        return 33;
    }
    alp_packet_destroy(parsed);
    parsed = NULL;

    if (alp_stream_parser_append(&parser, combined, 0U, &parsed) != 1) {
        return 34;
    }
    if (parsed == NULL || parsed->msg_id != 0x0102 || parsed->payload_length != sizeof(payload_b)) {
        alp_packet_destroy(parsed);
        return 35;
    }

    alp_packet_destroy(parsed);
    return 0;
}

static int test_corrupt_frame_before_valid_frame_is_skipped(void) {
    const uint8_t payload_bad[] = {'B', 'A', 'D'};
    const uint8_t payload_ok[] = {'O', 'K'};
    uint8_t bad_frame[64];
    uint8_t ok_frame[64];
    uint8_t combined[128];
    uint8_t parser_storage[128];
    alp_stream_parser_t parser;
    alp_packet_t *bad_packet = alp_packet_create(2, 0x1201, 0x3402, 0x0201, 0x01, 0, payload_bad, sizeof(payload_bad));
    alp_packet_t *ok_packet = alp_packet_create(2, 0x1201, 0x3402, 0x0202, 0x02, 0, payload_ok, sizeof(payload_ok));
    if (bad_packet == NULL || ok_packet == NULL) {
        alp_packet_destroy(bad_packet);
        alp_packet_destroy(ok_packet);
        return 40;
    }

    int bad_size = alp_packet_serialize(bad_packet, bad_frame, sizeof(bad_frame));
    int ok_size = alp_packet_serialize(ok_packet, ok_frame, sizeof(ok_frame));
    alp_packet_destroy(bad_packet);
    alp_packet_destroy(ok_packet);
    if (bad_size <= 0 || ok_size <= 0) {
        return 41;
    }

    bad_frame[bad_size - 1] ^= 0x01;
    memcpy(combined, bad_frame, (size_t)bad_size);
    memcpy(combined + bad_size, ok_frame, (size_t)ok_size);

    alp_stream_parser_init(&parser, parser_storage, sizeof(parser_storage));

    alp_packet_t *parsed = NULL;
    if (alp_stream_parser_append(&parser, combined, (size_t)(bad_size + ok_size), &parsed) != 1) {
        return 42;
    }
    if (parsed == NULL || parsed->msg_id != 0x0202 || parsed->payload_length != sizeof(payload_ok)) {
        alp_packet_destroy(parsed);
        return 43;
    }

    alp_packet_destroy(parsed);
    return 0;
}

int main(void) {
    int result = test_split_sof_is_preserved();
    if (result != 0) {
        return result;
    }

    result = test_invalid_prefix_before_split_sof_is_discarded();
    if (result != 0) {
        return result;
    }

    result = test_uint16_msg_id_round_trips();
    if (result != 0) {
        return result;
    }

    result = test_multiple_frames_are_parsed_sequentially();
    if (result != 0) {
        return result;
    }

    return test_corrupt_frame_before_valid_frame_is_skipped();
}
