#ifndef ALP_STREAM_PARSER_H
#define ALP_STREAM_PARSER_H

#include <stddef.h>
#include <stdint.h>

#include "communication_protocol.h"

typedef struct {
    uint8_t *buffer;
    size_t length;
    size_t capacity;
} alp_stream_parser_t;

void alp_stream_parser_init(alp_stream_parser_t *parser, uint8_t *buffer, size_t capacity);
void alp_stream_parser_reset(alp_stream_parser_t *parser);
int alp_stream_parser_append(
    alp_stream_parser_t *parser,
    const uint8_t *data,
    size_t data_length,
    alp_packet_t **out_packet
);

#endif
