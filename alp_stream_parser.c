#include <string.h>

#include "alp_stream_parser.h"

static void alp_stream_parser_discard(alp_stream_parser_t *parser, size_t count) {
    if (count >= parser->length) {
        parser->length = 0;
        return;
    }

    memmove(parser->buffer, parser->buffer + count, parser->length - count);
    parser->length -= count;
}

static int alp_stream_parser_find_sof(const alp_stream_parser_t *parser) {
    for (size_t i = 0; i + 1U < parser->length; ++i) {
        if (parser->buffer[i] == ALP_PACKET_SOF1 && parser->buffer[i + 1U] == ALP_PACKET_SOF2) {
            return (int)i;
        }
    }

    return -1;
}

void alp_stream_parser_init(alp_stream_parser_t *parser, uint8_t *buffer, size_t capacity) {
    parser->buffer = buffer;
    parser->length = 0;
    parser->capacity = capacity;
}

void alp_stream_parser_reset(alp_stream_parser_t *parser) {
    parser->length = 0;
}

int alp_stream_parser_append(
    alp_stream_parser_t *parser,
    const uint8_t *data,
    size_t data_length,
    alp_packet_t **out_packet
) {
    *out_packet = NULL;

    if (data_length > parser->capacity - parser->length) {
        alp_stream_parser_reset(parser);
        return -1;
    }

    memcpy(parser->buffer + parser->length, data, data_length);
    parser->length += data_length;

    while (1) {
        int sof_index = alp_stream_parser_find_sof(parser);
        if (sof_index < 0) {
            if (parser->length > 1U) {
                parser->buffer[0] = parser->buffer[parser->length - 1U];
                parser->length = 1U;
            }
            return 0;
        }

        if (sof_index > 0) {
            alp_stream_parser_discard(parser, (size_t)sof_index);
        }

        if (parser->length < ALP_HEADER_SIZE) {
            return 0;
        }

        uint16_t payload_length = (uint16_t)(((uint16_t)parser->buffer[10] << 8) | parser->buffer[11]);
        size_t frame_size = ALP_HEADER_SIZE + payload_length + ALP_CRC_SIZE;

        if (frame_size > parser->capacity) {
            alp_stream_parser_discard(parser, 1);
            continue;
        }

        if (parser->length < frame_size) {
            return 0;
        }

        if (alp_packet_deserialize(parser->buffer, frame_size, out_packet) == 0) {
            alp_stream_parser_discard(parser, frame_size);
            return 1;
        }

        alp_stream_parser_discard(parser, 1);
    }
}
