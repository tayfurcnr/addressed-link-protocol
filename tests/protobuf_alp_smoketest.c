#include "../alpcom/alpcom.h"
#include "../third_party/nanopb/pb_encode.h"

int main(void) {
    alp_ExamplePayload message = alp_ExamplePayload_init_zero;
    message.device_index = 7;
    message.value = 24.6f;

    uint8_t payload_buffer[64];
    pb_ostream_t stream = pb_ostream_from_buffer(payload_buffer, sizeof(payload_buffer));

    if (!pb_encode(&stream, alp_ExamplePayload_fields, &message)) {
        return 1;
    }

    alp_packet_t *packet = alp_packet_create(
        2,
        0x1201,
        ALP_BROADCAST_ID,
        0x0040,
        0x06,
        ALP_FLAG_PRIORITY,
        payload_buffer,
        (uint16_t)stream.bytes_written
    );
    if (packet == 0) {
        return 2;
    }

    uint8_t frame_buffer[128];
    int frame_size = alp_packet_serialize(packet, frame_buffer, sizeof(frame_buffer));
    alp_packet_destroy(packet);

    if (frame_size <= 0) {
        return 3;
    }

    return 0;
}
