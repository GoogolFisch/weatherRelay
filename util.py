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
        return Pair(self.dstMac,self.srcPort,self.dstPort)
    def getBytes(self):
        # uuid, src(mac,port),dst(mac,port)
        return struct.pack(">Qqiqi",
                           self.uuid & (~0xff),
                           self.srcMac,self.srcPort,
                           self.dstMac,self.dstPort)
    def reverse(self):
        return Pair(self.srcMax,self.dstPort,self.srcPort)

class Message:
    pair = None
    message = None
    def __init__(self,pair,message):
        self.pair = pair
        self.message = message
    def fromBytearray(message):
        index = 0
        mesList = []
        while len(message):
            pp = struct.unpack(">Qqiqii",message[index:])
            uuid, srcMac,srcPort, dstMac,dstPort,leng = pp
            pair = Pair(dstMax,srcPort,dstPort)
            pair.srcMac = srcMac
            pair.uuid = uuid
            pp = message[index:36 + leng + index]
            if(len(pp) != leng):break
            mesOut = Message(pair,pp)
            crcIndex = 8
            crc = 0
            # calc crc
            for b in range(crcIndex + index,36 + index + leng):
                crc ^= crc << 7
                crc += b
                crc &= 0xff_ff_ff_ff
                crc ^= crc >> 23 
            tstCrc = struct.unpack(">I",message[index + 36 + leng:])
            index += leng + 36 + 44
            if(tstCrc == crc):
                mesList.append(mesOut)
        return (mesList,index)


    def getBytes(self):
        data = self.pair.getBytes() + struct.pack(">i",len(self.message)) + self.message
        crcIndex = 8
        crc = 0
        # calc crc
        for b in range(crcIndex,len(data)):
            crc ^= crc << 7
            crc += b
            crc &= 0xff_ff_ff_ff
            crc ^= crc >> 23 
        data += struct.pack(">I",crc)
        return data
