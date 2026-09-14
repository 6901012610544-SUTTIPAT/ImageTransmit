#include <Arduino.h>

#define HC12 Serial1
#define PC_SERIAL Serial

const uint8_t PREAMBLE_1 = 0xAA;
const uint8_t PREAMBLE_2 = 0x55;

enum PacketType : uint8_t{
  PKT_DATA = 0x01,
  PKT_ACK = 0x02,
  PKT_NACK = 0x03,
  PKT_START = 0x04,
  PKY_END = 0x05
};

const uint8_t MAX_PAYLOAD = 48;
const unsigned long ACK_TIMEOUT_MS = 250;
const uint8_t MAX_RETRIES = 5;

struct Packet{
  uint8_t type;
  uint16_t seq;
  uint8_t len;
  uint8_t payload[MAX_PAYLOAD];
  uint8_t checksum;
};

uint8_t calculateChecksum(const Packet &pkt){
  uint8_t cs = pkt.type ^ (pkt.seq & 0xFF) ^ ((pkt.seq >> 8) & 0xFF) ^ pkt.len;
  for(uint8_t i = 0; i < pkt.len; i++) cs ^= pkt.payload[i];

  return cs;
}

//Send Packet Through HC-12 module
void sendPacket(const Packet &pkt){
  HC12.write(PREAMBLE_1);
  HC12.write(PREAMBLE_2);
  HC12.write(pkt.type);
  HC12.write((uint8_t)(pkt.seq & 0xFF));
  HC12.write((uint8_t)((pkt.seq >> 8) & 0xFF));
  HC12.write(pkt.len);

  if(pkt.len > 0){
    HC12.write(pkt.payload, pkt.len);
  }
  HC12.write(pkt.checksum);
  HC12.flush();
}

//Send ACK and NACK repeatedly
void sendResponse(PacketType type, uint16_t seq){
  Packet res;
  res.type = type;
  res.seq = seq;
  res.len = 0;
  res.checksum = calculateChecksum(res);
  sendPacket(res);
}

//Receieve Packet
bool receivePacket(Packet &pkt, unsigned long timeoutMs){
  unsigned long start = millis();
  while(millis() - start < timeoutMs){
    if(HC12.available() >= 2){
      if(HC12.read() == PREAMBLE_1 && HC12.peek() == PREAMBLE_2){
        HC12.read();

        unsigned long t2 = millis();
        while(HC12.available() < 4 && millis() - t2 < 100);
        if(HC12.available() < 4) return false;

        pkt.type = HC12.read();
        pkt.seq = HC12.read() | (HC12.read() << 8);
        pkt.len = HC12.read();

        if(pkt.len > MAX_PAYLOAD) return false;

        t2 = millis();
        while(HC12.available() < (pkt.len + 1) && millis() - t2 < 100);
        if(HC12.available() < (pkt.len + 1)) return false;

        for(uint8_t i = 0; i < pkt.len; i++){
          pkt.payload[i] = HC12.read();
        }
        pkt.checksum = HC12.read();

        if(calculateChecksum(pkt) == pkt.checksum){
          return true;
        }else{
          return false;
        }
      }
    }
  }
  return false;
}

//Transmitter routine
bool sendBlockWithRetry(Packet &pkt){
  pkt.checksum = calculateChecksum(pkt);
  for(uint8_t attempt = 0; attempt < MAX_RETRIES; attempt++){
    sendPacket(pkt);

    Packet ackPkt;
    if(receivePacket(ackPkt, ACK_TIMEOUT_MS)){
      if(ackPkt.type == PKT_ACK && ackPkt.seq == pkt.seq){
        return true;
      }
    }
    delay(10);
  }
  return false;
}

void handleTransmitter(){
  if(PC_SERIAL.available() > 0){
    static uint16_t txSeq = 0;
    Packet dataPkt;
    dataPkt.type = PKT_DATA;
    dataPkt.seq = txSeq;
    dataPkt.len = 0;

    while(PC_SERIAL.available() > 0 && dataPkt.len < MAX_PAYLOAD){
      dataPkt.payload[dataPkt.len++] = PC_SERIAL.read();
    }

    if(!sendBlockWithRetry(dataPkt)){
      PC_SERIAL.println("[ERROR] Packet loss! Destination unreachable.");
    }else{
      txSeq++;
    }
  }
}

//Receiver routine
void handleReceiver(){
  static uint16_t expectedSeq = 0;

  if(HC12.available() >= 2){
    Packet rxPkt;
    if(receivePacket(rxPkt, 50)){
      if(rxPkt.type == PKT_DATA){
        if(rxPkt.seq == expectedSeq){
          sendResponse(PKT_ACK, rxPkt.seq);

          PC_SERIAL.write(rxPkt.payload, rxPkt.len);
          expectedSeq++;
        }else if(rxPkt.seq < expectedSeq){
          sendResponse(PKT_ACK, rxPkt.seq);
        }else{
          sendResponse(PKT_NACK, rxPkt.seq);
        }
      }
    }
  }
}

void setup(){
  PC_SERIAL.begin(115200);
  HC12.begin(9600);
  PC_SERIAL.println(F("Mega 2560 Transceiver Ready."));
}

void loop(){
  //handleTransmitter();
  handleReceiver();
}