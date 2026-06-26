#include <stdlib.h>
#include <string.h>
#include "communication_protocol.h"

#ifndef ALP_LOG_ERROR
#define ALP_LOG_ERROR(...) ((void)0)
#endif

static void alp_packet_build_header(const alp_packet_t *packet, uint8_t header[ALP_HEADER_SIZE]) {
    header[0] = ALP_PACKET_SOF1;
    header[1] = ALP_PACKET_SOF2;
    header[2] = packet->version;
    header[3] = (uint8_t)((packet->src_id >> 8) & 0xFF);
    header[4] = (uint8_t)(packet->src_id & 0xFF);
    header[5] = (uint8_t)((packet->dst_id >> 8) & 0xFF);
    header[6] = (uint8_t)(packet->dst_id & 0xFF);
    header[7] = (uint8_t)((packet->msg_id >> 8) & 0xFF);
    header[8] = (uint8_t)(packet->msg_id & 0xFF);
    header[9] = packet->seq;
    header[10] = packet->flags;
    header[11] = (uint8_t)((packet->payload_length >> 8) & 0xFF);
    header[12] = (uint8_t)(packet->payload_length & 0xFF);
}

static uint16_t alp_crc16_update(uint16_t crc, const uint8_t *data, size_t length) {
    for (size_t i = 0; i < length; ++i) {
        crc ^= (uint16_t)(data[i] << 8);
        for (int bit = 0; bit < 8; ++bit) {
            if (crc & 0x8000U) {
                crc = (uint16_t)((crc << 1) ^ ALP_CRC16_POLYNOMIAL);
            } else {
                crc = (uint16_t)(crc << 1);
            }
        }
    }

    return crc;
}

uint16_t alp_crc16_calculate(const uint8_t *data, size_t length) {
    return alp_crc16_update(ALP_CRC16_INITIAL, data, length);
}

void alp_config_init(alp_config_t *config, uint16_t src_id, uint8_t version, uint8_t default_flags) {
    config->src_id = src_id;
    config->version = version;
    config->default_flags = default_flags;
}

alp_packet_t *alp_config_create_packet(
    const alp_config_t *config,
    uint16_t dst_id,
    uint16_t msg_id,
    uint8_t seq,
    const uint8_t *payload,
    uint16_t payload_length,
    int use_default_flags,
    uint8_t flags
) {
    return alp_packet_create(
        config->version,
        config->src_id,
        dst_id,
        msg_id,
        seq,
        use_default_flags ? config->default_flags : flags,
        payload,
        payload_length
    );
}

alp_packet_t *alp_packet_create(
    uint8_t version,
    uint16_t src_id,
    uint16_t dst_id,
    uint16_t msg_id,
    uint8_t seq,
    uint8_t flags,
    const uint8_t *payload,
    uint16_t payload_length
) {
    if (payload_length > ALP_MAX_PAYLOAD_SIZE) {
        ALP_LOG_ERROR("payload too large: %u\n", payload_length);
        return NULL;
    }

    alp_packet_t *packet = (alp_packet_t *)calloc(1, sizeof(*packet));
    if (packet == NULL) {
        ALP_LOG_ERROR("memory allocation failed\n");
        return NULL;
    }

    packet->version = version;
    packet->src_id = src_id;
    packet->dst_id = dst_id;
    packet->msg_id = msg_id;
    packet->seq = seq;
    packet->flags = flags;
    packet->payload_length = payload_length;

    if (payload_length > 0U) {
        packet->payload = (uint8_t *)malloc(payload_length);
        if (packet->payload == NULL) {
            ALP_LOG_ERROR("payload allocation failed\n");
            free(packet);
            return NULL;
        }
        memcpy(packet->payload, payload, payload_length);
    }

    return packet;
}

void alp_packet_destroy(alp_packet_t *packet) {
    if (packet == NULL) {
        return;
    }

    free(packet->payload);
    free(packet);
}

size_t alp_packet_total_size(const alp_packet_t *packet) {
    return ALP_HEADER_SIZE + packet->payload_length + ALP_CRC_SIZE;
}

uint16_t alp_packet_calculate_crc(const alp_packet_t *packet) {
    uint8_t header[ALP_HEADER_SIZE];
    alp_packet_build_header(packet, header);
    uint16_t crc = alp_crc16_update(ALP_CRC16_INITIAL, &header[2], ALP_HEADER_SIZE - 2U);
    if (packet->payload_length > 0U) {
        crc = alp_crc16_update(crc, packet->payload, packet->payload_length);
    }
    return crc;
}

int alp_packet_serialize(const alp_packet_t *packet, uint8_t *buffer, size_t buffer_size) {
    size_t total_size = alp_packet_total_size(packet);
    if (buffer_size < total_size) {
        ALP_LOG_ERROR("buffer too small: %zu < %zu\n", buffer_size, total_size);
        return -1;
    }

    uint8_t header[ALP_HEADER_SIZE];
    alp_packet_build_header(packet, header);
    memcpy(buffer, header, ALP_HEADER_SIZE);

    if (packet->payload_length > 0U) {
        memcpy(buffer + ALP_HEADER_SIZE, packet->payload, packet->payload_length);
    }

    uint16_t crc = alp_packet_calculate_crc(packet);

    buffer[ALP_HEADER_SIZE + packet->payload_length] = (uint8_t)((crc >> 8) & 0xFF);
    buffer[ALP_HEADER_SIZE + packet->payload_length + 1U] = (uint8_t)(crc & 0xFF);

    return (int)total_size;
}

int alp_packet_deserialize(
    const uint8_t *buffer,
    size_t buffer_size,
    alp_packet_t **out_packet
) {
    if (buffer_size < ALP_MIN_PACKET_SIZE) {
        ALP_LOG_ERROR("packet too short: %zu bytes\n", buffer_size);
        return -1;
    }

    if (buffer[0] != ALP_PACKET_SOF1 || buffer[1] != ALP_PACKET_SOF2) {
        ALP_LOG_ERROR("invalid SOF: 0x%02X 0x%02X\n", buffer[0], buffer[1]);
        return -1;
    }

    uint16_t payload_length = (uint16_t)(((uint16_t)buffer[11] << 8) | buffer[12]);
    size_t expected_size = ALP_HEADER_SIZE + payload_length + ALP_CRC_SIZE;
    if (buffer_size != expected_size) {
        ALP_LOG_ERROR("size mismatch: expected %zu, got %zu\n", expected_size, buffer_size);
        return -1;
    }

    uint16_t crc_received = (uint16_t)(((uint16_t)buffer[ALP_HEADER_SIZE + payload_length] << 8) |
                                       buffer[ALP_HEADER_SIZE + payload_length + 1U]);
    uint16_t crc_calculated = alp_crc16_calculate(&buffer[2], (ALP_HEADER_SIZE - 2U) + payload_length);

    if (crc_received != crc_calculated) {
        ALP_LOG_ERROR("CRC mismatch: received 0x%04X calculated 0x%04X\n", crc_received, crc_calculated);
        return -1;
    }

    const uint8_t *payload_ptr = payload_length > 0U ? &buffer[ALP_HEADER_SIZE] : NULL;
    alp_packet_t *packet = alp_packet_create(
        buffer[2],
        (uint16_t)(((uint16_t)buffer[3] << 8) | buffer[4]),
        (uint16_t)(((uint16_t)buffer[5] << 8) | buffer[6]),
        (uint16_t)(((uint16_t)buffer[7] << 8) | buffer[8]),
        buffer[9],
        buffer[10],
        payload_ptr,
        payload_length
    );
    if (packet == NULL) {
        return -1;
    }

    packet->crc16 = crc_received;
    *out_packet = packet;
    return 0;
}

#ifndef ALP_NO_DEMO_MAIN
#include <stdio.h>

static void print_hex(const uint8_t *data, size_t length) {
    for (size_t i = 0; i < length; ++i) {
        printf("%02X", data[i]);
        if (i + 1U < length) {
            printf(" ");
        }
    }
    printf("\n");
}

static void print_protocol_description(void) {
    printf("%s - %s\n", ALP_PROTOCOL_SHORT_NAME, ALP_PROTOCOL_NAME);
    printf("\n");
    printf("Packet layout:\n");
    printf("  SOF1           : 1 byte  (0x%02X)\n", ALP_PACKET_SOF1);
    printf("  SOF2           : 1 byte  (0x%02X)\n", ALP_PACKET_SOF2);
    printf("  VERSION        : 1 byte\n");
    printf("  SRC_ID         : 2 bytes (big-endian)\n");
    printf("  DST_ID         : 2 bytes (big-endian)\n");
    printf("  MSG_ID         : 2 bytes (big-endian)\n");
    printf("  SEQ            : 1 byte\n");
    printf("  FLAGS          : 1 byte\n");
    printf("  PAYLOAD_LENGTH : 2 bytes (big-endian)\n");
    printf("  PAYLOAD        : N bytes\n");
    printf("  CRC16          : 2 bytes (big-endian)\n");
    printf("\n");
    printf("Reserved IDs:\n");
    printf("  BROADCAST_ID   : 0x%04X\n", ALP_BROADCAST_ID);
    printf("\n");
    printf("CRC coverage:\n");
    printf("  VERSION | SRC_ID | DST_ID | MSG_ID | SEQ | FLAGS | PAYLOAD_LENGTH | PAYLOAD\n");
    printf("\n");
    printf("CRC parameters:\n");
    printf("  polynomial = 0x%04X\n", ALP_CRC16_POLYNOMIAL);
    printf("  initial    = 0x%04X\n", ALP_CRC16_INITIAL);
    printf("\n");
}

int main(void) {
    print_protocol_description();

    alp_config_t config;
    alp_config_init(&config, 0x1201, 2, ALP_FLAG_PRIORITY);

    const uint8_t payload[] = "TEMP=24.6C";
    alp_packet_t *packet = alp_config_create_packet(
        &config,
        0x3402,
        0x0031,
        0x05,
        payload,
        (uint16_t)(sizeof(payload) - 1U),
        0,
        ALP_FLAG_ACK_REQUIRED | ALP_FLAG_PRIORITY
    );
    if (packet == NULL) {
        return 1;
    }

    uint8_t buffer[256];
    int packet_size = alp_packet_serialize(packet, buffer, sizeof(buffer));
    if (packet_size < 0) {
        alp_packet_destroy(packet);
        return 1;
    }

    packet->crc16 = (uint16_t)(((uint16_t)buffer[packet_size - 2] << 8) | buffer[packet_size - 1]);

    printf("Demo packet:\n");
    printf("  payload        : %.*s\n", (int)packet->payload_length, (const char *)packet->payload);
    printf("  payload_length : %u\n", packet->payload_length);
    printf("  crc16          : 0x%04X\n", packet->crc16);
    printf("  packet_hex     : ");
    print_hex(buffer, (size_t)packet_size);
    printf("\n");

    alp_packet_t *parsed = NULL;
    if (alp_packet_deserialize(buffer, (size_t)packet_size, &parsed) != 0) {
        alp_packet_destroy(packet);
        return 1;
    }

    printf("Parsed packet:\n");
    printf("  version        : %u\n", parsed->version);
    printf("  src_id         : 0x%04X\n", parsed->src_id);
    printf("  dst_id         : 0x%04X\n", parsed->dst_id);
    printf("  msg_id         : 0x%04X\n", parsed->msg_id);
    printf("  seq            : 0x%02X\n", parsed->seq);
    printf("  flags          : 0x%02X\n", parsed->flags);
    printf("  is_broadcast   : %s\n", parsed->dst_id == ALP_BROADCAST_ID ? "true" : "false");
    printf("  ack_required   : %s\n", (parsed->flags & ALP_FLAG_ACK_REQUIRED) ? "true" : "false");
    printf("  priority       : %s\n", (parsed->flags & ALP_FLAG_PRIORITY) ? "true" : "false");

    alp_packet_destroy(parsed);
    alp_packet_destroy(packet);
    return 0;
}
#endif
