import serial
import time
import os
import struct

# --- Configurations ---
PORT = 'COM4'
BAUD_RATE = 115200
FOLDER_NAME = 'TestImage'
MAGIC_HEADER = b'IMG:'
VALID_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp')

# 1. ตรวจสอบโฟลเดอร์ TestImage
if not os.path.exists(FOLDER_NAME):
    os.makedirs(FOLDER_NAME)
    print(f"[Info] Created directory '{FOLDER_NAME}'. Please put image files inside and run again.")
    exit()

# กรองเฉพาะไฟล์รูปภาพตามนามสกุลที่กำหนด
image_files = [
    f for f in os.listdir(FOLDER_NAME) 
    if os.path.isfile(os.path.join(FOLDER_NAME, f)) and f.lower().endswith(VALID_EXTENSIONS)
]

if not image_files:
    print(f"[Warning] No image files found in '{FOLDER_NAME}/'")
    print(f"Supported formats: {', '.join(VALID_EXTENSIONS)}")
    exit()

# 2. แสดงรายการรูปภาพพร้อมขนาดไฟล์
print(f"\n{'='*15} Available Images in '{FOLDER_NAME}' {'='*15}")
for idx, file_name in enumerate(image_files, start=1):
    file_path = os.path.join(FOLDER_NAME, file_name)
    size_kb = os.path.getsize(file_path) / 1024
    print(f"  [{idx}] {file_name} ({size_kb:.1f} KB)")
print('='*55)

# 3. ให้ผู้ใช้เลือกหมายเลขไฟล์ภาพ
selected_index = None
while selected_index is None:
    user_input = input(f"Select image [1-{len(image_files)}] (or 'q' to quit): ").strip()
    if user_input.lower() == 'q':
        print("Transmission aborted by user.")
        exit()
    if user_input.isdigit():
        val = int(user_input)
        if 1 <= val <= len(image_files):
            selected_index = val - 1
        else:
            print(f"Please enter a number between 1 and {len(image_files)}.")
    else:
        print("Invalid input. Please enter a valid number.")

selected_file = image_files[selected_index]
IMAGE_PATH = os.path.join(FOLDER_NAME, selected_file)
file_size = os.path.getsize(IMAGE_PATH)

print(f"\nSelected: {selected_file}")
print(f"Total payload size: {file_size:,} bytes")

# 4. เชื่อมต่อ Serial และเริ่มกระบวนการส่ง
ser = serial.Serial(PORT, BAUD_RATE, timeout=5.0)
time.sleep(2)
ser.reset_input_buffer()
ser.reset_output_buffer()

# 4.1 ส่งคำสั่งรีเซ็ตระบบทั้งสองฝั่ง (Sync Reset)
print("Connecting and syncing with receiver...")
ser.write(bytes([0xFF]))
res = ser.read(1)
if res != b'K':
    print(f"[Fail] Cannot connect to receiver (Code: {res})")
    ser.close()
    exit()

print("[Success] Connected to receiver. Transmitting image data...")

# 4.2 รวม Header (8 ไบต์) เข้ากับข้อมูลภาพ
with open(IMAGE_PATH, 'rb') as f:
    full_payload = MAGIC_HEADER + struct.pack('>I', file_size) + f.read()

total_bytes = len(full_payload)
sent_bytes = 0
start_time = time.time()

# 4.3 ทยอยส่งทีละ Chunk (สูงสุด 48 ไบต์) พร้อมรอ Handshake 'K'
CHUNK_SIZE = 48
for i in range(0, total_bytes, CHUNK_SIZE):
    chunk = full_payload[i:i + CHUNK_SIZE]
    
    # ส่งขนาด Chunk (1 ไบต์) ตามด้วยข้อมูลไบต์จริง
    packet_to_arduino = bytes([len(chunk)]) + chunk
    ser.write(packet_to_arduino)
    
    # รอการยืนยัน ACK 'K' จาก Arduino
    ack = ser.read(1)
    if ack != b'K':
        print(f"\n[Error] Communication timeout/error at byte: {sent_bytes:,}")
        break
        
    sent_bytes += len(chunk)
    pct = (sent_bytes / total_bytes) * 100
    print(f"\rProgress: {pct:.1f}% ({sent_bytes:,}/{total_bytes:,} Bytes)", end="")

# 4.4 Flush บัฟเฟอร์ระบบก่อนปิดพอร์ต
ser.flush()
time.sleep(0.5)
ser.close()

elapsed = time.time() - start_time
print(f"\n[Success] Sending image complete (Elapsed time: {elapsed:.1f} seconds)")