#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "../alp_stream_parser.h"

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

int main(void) {
    int result = test_split_sof_is_preserved();
    if (result != 0) {
        return result;
    }

    result = test_invalid_prefix_before_split_sof_is_discarded();
    if (result != 0) {
        return result;
    }

    return test_uint16_msg_id_round_trips();
}
