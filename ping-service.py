
import acceptor
import socket
import util
import json
import select
import uuid
import struct


class Ping(acceptor.Acceptor):

    def __init__(self,data:str):
        pass

    def readWrite(self,data:util.Message) -> list[util.Message]:
        if(data is None):return []
        data2 = util.Message(data.pair.reverse(),data.message)
        return [data2]

    def close(self):
        #print(f"{len(self.connections)} of connections")
        pass
MAIN = Ping
