# Headder
- mes-type: 1Byte (merge down?)

## of type 0 (MSG)
- message-id: 58bit/7Bytes
- src: 2Bytes unused, 6 Bytes MAC, 4 Bytes Port
- dst: 2Bytes unused, 6 Bytes MAC, 4 Bytes Port
- len: 4Bytes of length
- data: n Bytes
- crc: 4 Bytes

## of type 1 (ACK)
- message-id: 58bit/7Bytes
- len: 4Bytes of length (here not used)
- crc: 4 Bytes

## of type 1 (NAK)
- message-id: 58bit/7Bytes
- len: 4Bytes of length (here not used)
- crc: 4 Bytes

## CRC
```
start with: int crc = 0
(for msg)bytes include src,dst,len,data
(for ack/nak)bytes include len
foreach byte:
    crc ^= crc << 7
    crc += byte
    crc ^= crc >> 23
this is the crc
```
