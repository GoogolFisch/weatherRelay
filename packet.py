
#from __future__ import absolute_import
import struct
import socket
import select
import uuid
import time


class Packet:
    @staticmethod
    def makeMessage(mes:bytes,dir):# -> Packet:
        pass
    
    @staticmethod
    def fromBytes(bdata:bytes):# -> Packet:
        proto = bdata[0]
        head = struct.unpack("!BBHHHBBH4s4s", bdata[:20])
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
