
#from __future__ import absolute_import
import struct
import socket
import select
import uuid
import time


class Packet:
    
    def __init__(self,message,dstIp,srcIp="127.0.0.1",ipV=4):
        pass

    @staticmethod
    def makeMessage(mes:bytes,dir):# -> Packet:
        pass
    
    @staticmethod
    def fromBytes(bdata:bytes):# -> Packet:
        proto = bdata[0]
        if(proto >> 4 == 4):#IPv4
            head = struct.unpack("!BBHHHBBH4s4s", bdata[:20])
            getPro,typeos,totalLen,idf,fr,ttl,upProto,crc,srcIp,dstIp = head
            print(f"IPv{getPro >> 4} hlen:{getPro & 15} TypeOfService:{typeos} totLength:{totalLen}")
            print(f"idf:{idf} NullBit:{fr >> 15} DontFrag:{(fr >> 14) & 1} MoreFrag:{(fr >> 13) & 1} FragOff:{fr & 0x1fff}")
            print(f"ttl:{ttl} upProto:{upProto} crc:{crc}")
            print(end=f"srcIp:{srcIp}/{".".join([str(x) for x in srcIp])} ")
            print(f"dstIp:{dstIp}/{".".join([str(x) for x in dstIp])}")
        if(proto >> 4 == 6):#IPv4
            head = struct.unpack("!IHBB16s16s", bdata[:20])
            getPro, payloadLen,nexHead,hoplimit,srcAddr,dstAddr= head
            print(f"IPv{getPro >> 28} Priorty:{(getPro >> 20) & 0xff} FlowLabel:{getPro & 0xf_ffff}")
            print(f"Payload-Length:{payloadLen} nexHead:{nexHead} HopLimit:{hoplimit}")
            print(f"srcAddress:{srcAddr}")
            print(f"dstAddress:{dstAddr}")
        print(proto,head)

    @staticmethod
    def getPacket(sock) -> bytes:
        # ???
        return sock.recv(1514) # ethernet frame limit

    @staticmethod
    def getL3Socket(interface:str):
        # this requires root!
        sock = socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_TCP)
        return sock
