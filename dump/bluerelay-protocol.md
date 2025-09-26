# Headder
- mes-type: 1Byte (merge down?)

## of type 0 (MSG)
- message-id: 58bit/7Bytes
- src: 2Bytes unused, 6 Bytes MAC
- dst: 2Bytes unused, 6 Bytes MAC
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
