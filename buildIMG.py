import serial
import time
import struct

PORT = 'COM3'
BAUD_RATE = 115200
OUTPUT_IMAGE = 'received_image.jpg'
MAGIC_HEADER = b'IMG:'

ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
time.sleep(2)
ser.reset_input_buffer()

print(f"Connecting to port {PORT}, waiting for transmitter...")

buffer = bytearray()
while True:
    byte = ser.read(1)
    if not byte:
        continue
    buffer.extend(byte)
    if buffer.endswith(MAGIC_HEADER):
        print("Found picture header.")
        break

size_bytes = ser.read(4)
while len(size_bytes) < 4:
    size_bytes += ser.read(4 - len(size_bytes))

expected_size = struct.unpack('>I', size_bytes)[0]
print(f"File size detected: {expected_size:,} Bytes ({expected_size / 1024:.2f} KB)")

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

with open(OUTPUT_IMAGE, 'wb') as f:
    f.write(received_bytes)

print(f"[Success] save file '{OUTPUT_IMAGE}' complete.")
ser.close()