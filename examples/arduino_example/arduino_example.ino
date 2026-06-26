#include <alpcom.h>

static uint8_t stream_buffer[256];
static uint8_t read_buffer[64];
static alp_stream_parser_t parser;

void setup() {
  Serial.begin(115200);
  delay(1000);

  alp_stream_parser_init(&parser, stream_buffer, sizeof(stream_buffer));
  Serial.println("ALP receiver ready");
}

void loop() {
  size_t count = Serial.readBytes((char *)read_buffer, sizeof(read_buffer));
  if (count == 0) {
    return;
  }

  alp_packet_t *packet = NULL;
  int status = alp_stream_parser_append(&parser, read_buffer, count, &packet);

  while (status > 0 && packet != NULL) {
    if (packet->msg_id == ALP_MSG_EXAMPLEPAYLOAD) {
      alp_ExamplePayload payload = alp_ExamplePayload_init_zero;
      pb_istream_t stream = pb_istream_from_buffer(packet->payload, packet->payload_length);

      if (pb_decode(&stream, alp_ExamplePayload_fields, &payload)) {
        Serial.print("src_id=");
        Serial.print(packet->src_id, HEX);
        Serial.print(" device_index=");
        Serial.print(payload.device_index);
        Serial.print(" value=");
        Serial.println(payload.value, 4);
      } else {
        Serial.println("ExamplePayload decode failed");
      }
    } else {
      Serial.print("Unknown msg_id=0x");
      Serial.println(packet->msg_id, HEX);
    }

    alp_packet_destroy(packet);
    packet = NULL;
    status = alp_stream_parser_append(&parser, read_buffer, 0, &packet);
  }

  if (status < 0) {
    Serial.println("ALP parse error");
  }
}
