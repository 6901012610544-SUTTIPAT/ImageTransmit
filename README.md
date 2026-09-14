# การทดลองนี้ยังไม่เป็นไปตาม TOR

## Requirement
- Library serial ของภาษา Python
```
pip install pyserial
```

## ข้อสังเกตจากการต่อสายไฟ
บอร์ดทั้งสองจะติดต่อกันได้เมื่อนำขา Rx ของ HC12 ต่อกับขา Tx1 ของ Arduino ในทางกลับกันขา Tx ของ HC12 ก็ต่อเข้ากับขาของ Rx1 บน Arduino

## วิธีการใช้งาน
1. Upload sketch ไปยังบอร์ดทั้งสอง
2. เมื่อ Upload เสร็จห้ามเปิด Serial Monitor
3. เปิด run.bat
4. เลือกโหมดการทำงาน
