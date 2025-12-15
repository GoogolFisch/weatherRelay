import socket

so = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
so.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)

def stuff(name=b"name",addr="172.31.255.255",port=2048):
    so.sendto(name,(addr,port))
    while True:
        print(so.recvfrom(1024))

so6 = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)
def stuff6(name=b"name",addr="10::1",port=2048):
    so6.sendto(name,(addr,port))
    while True:
        print(so6.recvfrom(1024))
