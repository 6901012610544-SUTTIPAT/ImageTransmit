#include <Arduino.h>

#define HC12 Serial1      // Pin 19 (RX1), Pin 18 (TX1)
#define PC_SERIAL Serial  // USB Port ต่อคอมพิวเตอร์

const uint8_t PREAMBLE_1 = 0xAA;
const uint8_t PREAMBLE_2 = 0x55;
const uint8_t MAX_PAYLOAD = 48;
const unsigned long ACK_TIMEOUT_MS = 300;
const uint8_t MAX_RETRIES = 5;

enum PacketType : uint8_t {
  PKT_DATA  = 0x01,
  PKT_ACK   = 0x02,
  PKT_START = 0x03
};

struct Packet {
  uint8_t  type;
  uint16_t seq;
  uint8_t  len;
  uint8_t  payload[MAX_PAYLOAD];
  uint8_t  checksum;
};

uint8_t calculateChecksum(const Packet &pkt) {
  uint8_t cs = pkt.type ^ (pkt.seq & 0xFF) ^ ((pkt.seq >> 8) & 0xFF) ^ pkt.len;
  for (uint8_t i = 0; i < pkt.len; i++) {
    cs ^= pkt.payload[i];
  }
  return cs;
}

void sendRfPacket(const Packet &pkt) {
  HC12.write(PREAMBLE_1);
  HC12.write(PREAMBLE_2);
  HC12.write(pkt.type);
  HC12.write((uint8_t)(pkt.seq & 0xFF));
  HC12.write((uint8_t)((pkt.seq >> 8) & 0xFF));
  HC12.write(pkt.len);
  if (pkt.len > 0) {
    HC12.write(pkt.payload, pkt.len);
  }
  HC12.write(pkt.checksum);
  HC12.flush();
}

void sendRfAck(uint16_t seq) {
  Packet ack;
  ack.type = PKT_ACK;
  ack.seq = seq;
  ack.len = 0;
  ack.checksum = calculateChecksum(ack);
  sendRfPacket(ack);
}

bool receiveRfPacket(Packet &pkt, unsigned long timeoutMs) {
  unsigned long start = millis();
  while (millis() - start < timeoutMs) {
    if (HC12.available() >= 2) {
      if (HC12.read() == PREAMBLE_1 && HC12.peek() == PREAMBLE_2) {
        HC12.read(); // กิน PREAMBLE_2

        unsigned long t2 = millis();
        while (HC12.available() < 4 && millis() - t2 < 120);
        if (HC12.available() < 4) return false;

        pkt.type = HC12.read();
        pkt.seq = HC12.read() | (HC12.read() << 8);
        pkt.len = HC12.read();

        if (pkt.len > MAX_PAYLOAD) return false;

        t2 = millis();
        while (HC12.available() < (pkt.len + 1) && millis() - t2 < 120);
        if (HC12.available() < (pkt.len + 1)) return false;

        for (uint8_t i = 0; i < pkt.len; i++) {
          pkt.payload[i] = HC12.read();
        }
        pkt.checksum = HC12.read();

        if (calculateChecksum(pkt) == pkt.checksum) {
          return true;
        }
        return false;
      }
    }
  }
  return false;
}

bool sendWithRetry(Packet &pkt) {
  pkt.checksum = calculateChecksum(pkt);
  for (uint8_t attempt = 0; attempt < MAX_RETRIES; attempt++) {
    sendRfPacket(pkt);

    Packet ackPkt;
    if (receiveRfPacket(ackPkt, ACK_TIMEOUT_MS)) {
      if (ackPkt.type == PKT_ACK && ackPkt.seq == pkt.seq) {
        return true;
      }
    }
    delay(15);
  }
  return false;
}

// ---------------- ฝั่งส่ง (TX Routine) ----------------
static uint16_t currentTxSeq = 0;

void handleTransmitter() {
  if (PC_SERIAL.available() > 0) {
    uint8_t targetLen = PC_SERIAL.read(); // ไบต์แรกระบุขนาด Chunk (1 - 48) หรือ 0xFF สำหรับ START

    if (targetLen == 0xFF) { 
      // คำสั่ง Reset / Start รอบใหม่จาก Python
      Packet startPkt;
      startPkt.type = PKT_START;
      startPkt.seq = 0;
      startPkt.len = 0;
      currentTxSeq = 0;

      if (sendWithRetry(startPkt)) {
        PC_SERIAL.write('K');
      } else {
        PC_SERIAL.write('E');
      }
      return;
    }

    if (targetLen > MAX_PAYLOAD || targetLen == 0) return;

    Packet dataPkt;
    dataPkt.type = PKT_DATA;
    dataPkt.seq = currentTxSeq;
    dataPkt.len = targetLen;

    // อ่านข้อมูลจาก USB ให้ครบตามจำนวน targetLen ป้องกันปัญหาเศษหลุด
    uint8_t bytesRead = 0;
    unsigned long startWait = millis();
    while (bytesRead < targetLen && (millis() - startWait < 500)) {
      if (PC_SERIAL.available() > 0) {
        dataPkt.payload[bytesRead++] = PC_SERIAL.read();
      }
    }

    if (bytesRead == targetLen) {
      if (sendWithRetry(dataPkt)) {
        currentTxSeq++;
        PC_SERIAL.write('K'); // ยืนยันถึง Python: ปลายทางได้รับและ ACK แล้ว
      } else {
        PC_SERIAL.write('E'); // วิทยุล้มเหลว
      }
    }
  }
}

// ---------------- ฝั่งรับ (RX Routine) ----------------
static uint16_t expectedRxSeq = 0;

void handleReceiver() {
  if (HC12.available() >= 2) {
    Packet rxPkt;
    if (receiveRfPacket(rxPkt, 40)) {
      if (rxPkt.type == PKT_START) {
        expectedRxSeq = 0;
        sendRfAck(rxPkt.seq);
      } 
      else if (rxPkt.type == PKT_DATA) {
        if (rxPkt.seq == expectedRxSeq) {
          sendRfAck(rxPkt.seq);
          PC_SERIAL.write(rxPkt.payload, rxPkt.len);
          PC_SERIAL.flush();
          expectedRxSeq++;
        } else if (rxPkt.seq < expectedRxSeq) {
          // ได้รับแพ็กเก็ตซ้ำ ส่ง ACK ยืนยันซ้ำอีกครั้ง
          sendRfAck(rxPkt.seq);
        }
      }
    }
  }
}

void setup() {
  PC_SERIAL.begin(115200);
  HC12.begin(9600);
}

void loop() {
  handleTransmitter();
  handleReceiver();
}