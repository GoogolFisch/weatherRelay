import struct
import uuid


class Pair:
    srcMac = uuid.getnode()
    dstMac = 0
    srcPort = 0
    dstPort = 0
    uuid = 0
    def __init__(self,dstMac,srcPort,dstPort):
        self.dstMac = dstMac
        self.srcPort = srcPort
        self.dstPort = dstPort
        self.uuid = uuid.uuid4().int & ((1 << 64) - 1)
    def reUse(self):
        self.uuid = uuid.uuid4().int & ((1 << 64) - 1)
    def copy(self):
        return Pair(self.dstMax,self.srcPort,self.dstPort)
    def getBytes(self):
        # uuid, src(mac,port),dst(mac,port)
        return struct.pack("<l>l>i>l>i",
                           self.uuid & (~0xff),
                           self.srcMac,self.srcPort,
                           self.dstMac,self.dstPort)

class Message:
    pair = None
    def __init__(self,pair,message):
        self.pair = pair
    def getBytes(self):
        data = piar.getBytes() + struct.pack(">i",len(message)) + message
        crcIndex = 8
        crc = 0
        # calc crc
        for b in range(crcIndex,len(data)):
            crc ^= crc << 7
            crc += b
            crc &= 0xff_ff_ff_ff
            crc ^= crc >> 23 
        data += struct.pack(">i",crc)
        return data
