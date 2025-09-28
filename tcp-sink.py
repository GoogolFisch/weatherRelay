
import acceptor
import socket
import util
import json
import select
import uuid
import struct


class TcpBlueConn:
    pair = None
    socket = None
    id = 0
    def __init__(self,pair,socket):
        self.pair = pair
        self.socket = socket
        self.id = uuid.uuid4().int & 0xffff_ffff

class TcpSink(acceptor.Acceptor):
    connections = []
    socketTbc = {}
    idTbc = {}

    server = None
    pair = None

    HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
    PORT = 65432  # Port to listen on (non-privileged ports are > 1023)
    POINT_PORT = 22
    def __init__(self,data:str):
        self.POINT_PORT = data["socPort"]
        if(type(data) == str):
            jjso = json.loads(data)
        else:jjso = data
        self.pair = util.Pair(data["dstMac"],2202,2202)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((self.HOST, self.PORT))
        self.server.listen()
        #server.setblocking(0)
        self.server.settimeout(0)
        self.connections.append(self.server)
        self.socketTbc = {}
        self.idTbc = {}

    def readDataFromSocket(self, socket):
        data = ''
        buffer = b''
        try:
            while True:
                data = socket.recv(4096)
                if not data:break
                buffer += data

        except Exception as error: 
            print(
            type(error).__name__,          # TypeError
            __file__,                  # /tmp/example.py
            error.__traceback__.tb_lineno  # 2
            )
            print(f'socket.error - ({error})')

        if data:
            print('received', buffer)
        else:
            self.connections.remove(socket)
            tbc = self.socketTbc[socket]
            self.socketTbc.remove(socket)
            self.idTbc.remove(tbc.id)
        return buffer


    def readWrite(self,data:util.Message) -> list[util.Message]:
        readable, writable, exceptional = select.select(
        self.connections, [], self.connections, 1)
        outputList = []
        for s in readable:
            if s is self.server:
                connection, client_address = s.accept()
                print(f"{connection=} {client_address=}")
                connection.setblocking(0)
                self.connections.append(connection)
                continue
            else:
                dda = self.readDataFromSocket(s)
                # idk
                outputList.append(util.Message(self.pair,dda))
                print(self.socketTbc,s)
                bb = self.socketTbc.get(s)
                if(bb is None):
                    bb = TcpBlueConn(self.pair,s)
                    self.socketTbc[s] = bb
                    self.idTbc[bb.id] = bb
                outputList.append(struct.pack(">l>i",bb.id,len(dda)) + dda)
                # sending over br
        if data is not None:
            cid,len = struct.unpack(">l>i",data)
            mms = data[6:6+len]
            print(data)
            pairing = self.idTbc.get(cid)
            # sending over tcp
            if(paring is not None):
                # reusing build socket
                pairing.socket.send(mms)
            else:
                soc = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                soc.connect((HOST,POINT_PORT))
                tbc = TcpBlueConn(data.pair,soc)
                self.connections.append(soc)
                self.idTbc[cid] = tbc
                self.socketTbc[soc] = tbc
                soc.send(mms)



        # send con-id stuff, with len + data
        return outputList

    def close(self):
        print(f"{len(self.connections)} of connections")
        for c in self.connections:
            c.close()
        self.server.close()
MAIN = TcpSink
