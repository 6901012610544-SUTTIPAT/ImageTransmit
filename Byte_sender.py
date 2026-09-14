import serial
import time
import os
import struct

PORT = 'COM4'
BAUD_RATE = 115200
IMAGE_PATH = "./img/test1.jpg"
MAGIC_HEADER = b'IMG:'

if not os.path.exists(IMAGE_PATH):
    print(f"File not found: {IMAGE_PATH}")
    exit()

file_size = os.path.getsize(IMAGE_PATH)
print(f"Start sending file: {IMAGE_PATH} ({file_size:,} ไบต์)")

ser = serial.Serial(PORT, BAUD_RATE, timeout=5.0)
time.sleep(2)
ser.reset_input_buffer()
ser.reset_output_buffer()

#1.ส่งคำสั่งรีเซ็ตระบบทั้งสองฝั่ง (Sync Reset)
print("Connecting, and Sync with receiver...")
ser.write(bytes([0xFF]))
res = ser.read(1)
if res != b'K':
    print(f"[Fail] Cannot connect to receiver (Code: {res})")
    ser.close()
    exit()

print("[Success] Start sending...")

#2.รวม Header (8 ไบต์) เข้ากับข้อมูลภาพทั้งหมด
with open(IMAGE_PATH, 'rb') as f:
    full_payload = MAGIC_HEADER + struct.pack('>I', file_size) + f.read()

total_bytes = len(full_payload)
sent_bytes = 0
start_time = time.time()

#3.ทยอยส่งทีละ Chunk (สูงสุด 48 ไบต์) พร้อมรอ Handshake 'K' ทุกครั้ง
CHUNK_SIZE = 48
for i in range(0, total_bytes, CHUNK_SIZE):
    chunk = full_payload[i:i + CHUNK_SIZE]
    
    #ส่งขนาด Chunk (1 ไบต์) ตามด้วยเนื้อข้อมูลจริง
    packet_to_arduino = bytes([len(chunk)]) + chunk
    ser.write(packet_to_arduino)
    
    #รอการยืนยัน ACK จากปลายทาง
    ack = ser.read(1)
    if ack != b'K':
        print(f"\n[Error] Connection lost at byte: {sent_bytes:,}")
        break
        
    sent_bytes += len(chunk)
    pct = (sent_bytes / total_bytes) * 100
    print(f"\rProgress: {pct:.1f}% ({sent_bytes:,}/{total_bytes:,} Bytes)", end="")

#4.Flush บัฟเฟอร์ระบบก่อนปิดพอร์ต เพื่อป้องกันข้อมูลท้ายไฟล์ถูกตัดทิ้ง
ser.flush()
time.sleep(0.5)
ser.close()

elapsed = time.time() - start_time
print(f"\n[Success] Sending image complete  (estimated time: {elapsed:.1f} seconds)")