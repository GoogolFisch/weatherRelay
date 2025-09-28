
import acceptor
import socket
import util
import json
import select


class TcpBlueConn:
    pair = None
    socket = None
    id = 0
    def __init__(self,pair,socket):
        self.pair = pair
        self.socket = socket

class TcpSink(acceptor.Acceptor):
    connections = []
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

    def readDataFromSocket(self, socket):
        data = ''
        buffer = ''
        try:
            while True:
                data = socket.recv(4096)
                if not data:break
                buffer += data

        except Except as error: 
            print(
            type(error).__name__,          # TypeError
            __file__,                  # /tmp/example.py
            error.__traceback__.tb_lineno  # 2
            )
            print(f'socket.error - ({error})')

        if data:
            print('received', buffer)
        else:
            print('disconnected')
        return buffer


    def readWrite(self,data:list[util.Message]) -> list[util.Message]:
        readable, writable, exceptional = select.select(
        self.connections, [], self.connections, 1)
        outputList = []
        for s in readable:
            if s is server_socket:
                connection, client_address = s.accept()
                print(f"{connection=} {client_address=}")
                connection.setblocking(0)
                self.connections.append(connection)
                continue
            else:
                dda = self.readDataFromSocket(s)
                print(dda)
        for msg in data:
            print(msg)


        # send con-id stuff, with len + data
        return outputList

    def close(self):
        self.server.close()
MAIN = TcpSink
