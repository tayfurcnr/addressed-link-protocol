#ifndef COMMUNICATION_PROTOCOL_H
#define COMMUNICATION_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#define ALP_PACKET_SOF1 0xAA
#define ALP_PACKET_SOF2 0x55
#define ALP_BROADCAST_ID 0xFFFF
#define ALP_PROTOCOL_SHORT_NAME "ALP"
#define ALP_PROTOCOL_NAME "Addressed Link Protocol"
#define ALP_HEADER_SIZE 13
#define ALP_CRC_SIZE 2
#define ALP_MIN_PACKET_SIZE (ALP_HEADER_SIZE + ALP_CRC_SIZE)
#define ALP_MAX_PAYLOAD_SIZE 65535U
#define ALP_CRC16_POLYNOMIAL 0x1021U
#define ALP_CRC16_INITIAL 0xFFFFU

typedef enum {
    ALP_FLAG_NONE = 0x00,
    ALP_FLAG_ACK_REQUIRED = 0x01,
    ALP_FLAG_COMPRESSED = 0x02,
    ALP_FLAG_ENCRYPTED = 0x04,
    ALP_FLAG_RETRY = 0x08,
    ALP_FLAG_PRIORITY = 0x10
} alp_packet_flags_t;

typedef struct {
    uint8_t version;
    uint16_t src_id;
    uint8_t default_flags;
} alp_config_t;

typedef struct {
    uint8_t version;
    uint16_t src_id;
    uint16_t dst_id;
    uint16_t msg_id;
    uint8_t seq;
    uint8_t flags;
    uint16_t payload_length;
    uint8_t *payload;
    uint16_t crc16;
} alp_packet_t;

uint16_t alp_crc16_calculate(const uint8_t *data, size_t length);
void alp_config_init(alp_config_t *config, uint16_t src_id, uint8_t version, uint8_t default_flags);
alp_packet_t *alp_config_create_packet(
    const alp_config_t *config,
    uint16_t dst_id,
    uint16_t msg_id,
    uint8_t seq,
    const uint8_t *payload,
    uint16_t payload_length,
    int use_default_flags,
    uint8_t flags
);
alp_packet_t *alp_packet_create(
    uint8_t version,
    uint16_t src_id,
    uint16_t dst_id,
    uint16_t msg_id,
    uint8_t seq,
    uint8_t flags,
    const uint8_t *payload,
    uint16_t payload_length
);
void alp_packet_destroy(alp_packet_t *packet);
size_t alp_packet_total_size(const alp_packet_t *packet);
uint16_t alp_packet_calculate_crc(const alp_packet_t *packet);
int alp_packet_serialize(const alp_packet_t *packet, uint8_t *buffer, size_t buffer_size);
int alp_packet_deserialize(const uint8_t *buffer, size_t buffer_size, alp_packet_t **out_packet);

#endif
