#include "../alpcom/alpcom.h"

int main(void) {
    alp_packet_t *packet = alp_packet_create(
        1,
        0x1001,
        ALP_BROADCAST_ID,
        0x42,
        0x01,
        ALP_FLAG_PRIORITY,
        (const uint8_t *)"OK",
        2
    );

    if (packet == 0) {
        return 1;
    }

    alp_packet_destroy(packet);
    return 0;
}
