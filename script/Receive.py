import serial
import time
import struct
import os
from datetime import datetime

# --- การตั้งค่าโฟลเดอร์และพอร์ต ---
PORT = 'COM3'
BAUD_RATE = 115200
OUTPUT_DIR = 'ReceivedImages'  # ชื่อโฟลเดอร์ปลายทางที่ต้องการเก็บไฟล์
FILE_PREFIX = 'image'          # คำนำหน้าชื่อไฟล์
MAGIC_HEADER = b'IMG:'

# 1. ตรวจสอบและสร้างโฟลเดอร์สำหรับเซฟภาพหากยังไม่มี
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)
    print(f"สร้างโฟลเดอร์จัดเก็บภาพ: '{OUTPUT_DIR}' เรียบร้อย")

ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
time.sleep(2)
ser.reset_input_buffer()

print(f"Connecting to port {PORT}, waiting for transmitter...")

# 2. รอตรวจจับ Magic Header
buffer = bytearray()
while True:
    byte = ser.read(1)
    if not byte:
        continue
    buffer.extend(byte)
    if buffer.endswith(MAGIC_HEADER):
        print("Found picture header.")
        break

# 3. อ่านนามสกุลไฟล์ 4 ไบต์ (ที่ส่งมาจาก Transmit.py)
ext_bytes = bytearray()
while len(ext_bytes) < 4:
    chunk = ser.read(4 - len(ext_bytes))
    if chunk:
        ext_bytes.extend(chunk)

file_ext = ext_bytes.decode('ascii', errors='ignore').rstrip('\x00')
if not file_ext:
    file_ext = 'jpg'  # ค่าสำรองกรณีตรวจไม่พบนามสกุล

# 4. อ่านขนาดไฟล์จริง 4 ไบต์
size_bytes = bytearray()
while len(size_bytes) < 4:
    chunk = ser.read(4 - len(size_bytes))
    if chunk:
        size_bytes.extend(chunk)

expected_size = struct.unpack('>I', size_bytes)[0]
print(f"File detected: .{file_ext} | Size: {expected_size:,} Bytes ({expected_size / 1024:.2f} KB)")

# 5. รับข้อมูลภาพจนครบตามขนาดจริง
received_bytes = bytearray()
start_time = time.time()

while len(received_bytes) < expected_size:
    remaining = expected_size - len(received_bytes)
    bytes_to_read = min(ser.in_waiting if ser.in_waiting > 0 else 1, remaining)
    chunk = ser.read(bytes_to_read)
    
    if chunk:
        received_bytes.extend(chunk)
        pct = (len(received_bytes) / expected_size) * 100
        print(f"\rReceiving: {pct:.1f}% ({len(received_bytes):,}/{expected_size:,} Bytes)", end="")

elapsed = time.time() - start_time
print(f"\n[Success] Getting data {len(received_bytes):,} Byte, time elapsed {elapsed:.1f} seconds")

# 6. สร้างชื่อไฟล์ตามรูปแบบ: ชื่อ_ปีเดือนวัน_ชั่วโมงนาทีวินาที.นามสกุล
timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
output_filename = f"{FILE_PREFIX}_{timestamp_str}.{file_ext}"
output_path = os.path.join(OUTPUT_DIR, output_filename)

# 7. บันทึกไฟล์ลงในโฟลเดอร์เป้าหมาย
with open(output_path, 'wb') as f:
    f.write(received_bytes)

print(f"[Success] save file to '{output_path}' complete.")
ser.close()