# การทดลองนี้ยังไม่เป็นไปตาม TOR

## Requirement
1. Arduino Mega 2560 2 ตัว
2. HC12 rf module 2 ตัว
3. สายไฟ
4. Library serial ของภาษา Python
```
pip install pyserial
```

## ข้อสังเกตจากการต่อสายไฟ
  บอร์ดท้องสองจะติดต่อกันได้ เมื่อนำสาย Rx ของ HC12 ต่อกับขา Tx1 ของ Arduino ในทางกลับกัน Tx ของ HC12 ก็ต่อเข้ากับขาของ Rx1 บน Arduino

## วิธีการใช้งาน
1. จะมีบอร์ดที่เป็น Ground station ให้ Upload ไฟล์ Receive.ino
2. จะมีบอร์ดที่เป็น OBC ให้ Upload ไฟล์ Transmit.ino
3. หลังจากupload แล้วห้ามเปิด serial monitor
4. Ground station ใช้ builIMG.py
5. OBC ใช้ Byte_sender.py
