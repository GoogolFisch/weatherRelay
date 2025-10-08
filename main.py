#!/usr/bin/env python3

import bluetooth
import scapy.all
import json
import select
import time
import threading
import random
import socket
import os


CONFIG_FILE = "./config.json"
with open(CONFIG_FILE,"r") as fptr:
    config_data = json.load(fptr)

# listening (socket)
socketing = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
hereIp4 = "127.0.0.1"
hereIp6 = "::1"
try:
    socketing.connect(("99.99.99.99",64444))
    hereIp4 = socketing.getsockname()[0]
except:pass
socketing.close()
socketing = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)
try:
    socketing.connect(("2001::1",64444))
    hereIp6 = socketing.getsockname()[0]
except:pass
socketing.close()
print(f"I am: {hereIp4} , {hereIp6} !")

messageQueue = []
redirectMap = {} # this will be generated
# TODO add more features here
myIp4 = config_data.get("ip4") or "10.x.x.x"
myIp6 = config_data.get("ip6") or "10:x:x:x:x:x:x:x"
broadIp4 = (config_data.get("ip4") or "10.x.x.x").replace("x","255")
broadIp6 = (config_data.get("ip6") or "10:x:x:x:x:x:x:x").replace("x","ffff")
beginnIp4 = myIp4[:myIp4.index("x")]
beginnIp6 = myIp6[:myIp6.index("x")]
while("x" in myIp4):
    myIp4 = myIp4.replace("x",str(random.randrange(256)),1)
while("x" in myIp6):
    myIp6 = myIp6.replace("x",hex(random.randrange(0xffff))[2:],1)
print(f"currently using: {myIp4} , {myIp6} as addresses!")
running = True
timeToDeath = config_data.get("ttd") or 10

if(config_data["doSetup"]):
    # adding virtual interface ...
    # https://linuxconfig.org/configuring-virtual-network-interfaces-in-linux
    os.system('modprobe dummy')
    os.system('ip link add veth0 type dummy') # void ethernet
    os.system('ip link show veth0') # testing if veth0 exists
    os.system('ifconfig veth0 hw ether 11:22:33:44:55:66') # testing if veth0 exists
    os.system('ip addr add 172.16.0.0/12 brd + dev veth0 label veth0:0') # testing if veth0 exists
    os.system('ip addr add 10::/16 dev veth0 label veth0:0') # testing if veth0 exists
    os.system('ip link set dev veth0 up') # starting the interface

    #os.system('ip route add 172.16.0.0/16 via 172.17.0.1')
    #os.system('arp -s 172.17.0.1 01:02:03:04:05:06')
    # bluetooth setup
    os.system('hciconfig hci0 piscan')

# starting main part
connections = []
blueServer = None
uuid = config_data["uuid"]
# setup server
if(config_data["server"]):
    blueServer = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    blueServer.bind(("",bluetooth.PORT_ANY))
    blueServer.listen(8)

    port = blueServer.getsockname()[1]
    bluetooth.advertise_service(blueServer, "BlueRelay", service_id=uuid,
                                service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
                                profiles=[bluetooth.SERIAL_PORT_PROFILE]
                                )
    connections.append(blueServer)
    print("started Server")

# setup client
if(config_data["client"]):
    services = bluetooth.find_service(uuid=uuid,address=None)
    print(services)
    for serv in services:
        port = serv["port"]
        name = serv["name"]
        host = serv["host"]
        print("Connecting to \"{}\" on {}".format(name, host))
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((host, port))
        connections.append(sock)

def bindIpSocket(pkg,defaultVec,cmpTime,sock = None) -> socket.socket:
    (dstSock,dstTime,dstHops) = redirectMap.get(pkg.dst) or defaultVec
    (srcSock,srcTime,srcHops) = redirectMap.get(pkg.src) or defaultVec
    # clean-up
    if(srcTime < cmpTime - timeToDeath):
        # if too old!
        if(srcSock is not None):
            redirectMap.pop(pkg.src)
        srcHops = 999
    if(srcHops >= pkg.hops() and sock is not None):
        # renew the src
        redirectMap[pkg.src] = (sock,cmpTime,pkg.hops())
        print(f"{pkg.src} -> {(sock,cmpTime,pkg.hops())}")
    if(dstTime < cmpTime - timeToDeath and dstSock is not None):
        # if too old!
        redirectMap.pop(pkg.dst)
        dstSock = None
    return dstSock

def trySendPacket(pkg,dstSock=None):
    # limit the number of hops!
    if(pkg.version == 4):
        del(pkg.chksum)
        pkg.ttl -= 1
        if(pkg.ttl <= 0):return
    elif(pkg.version == 6):
        pkg.hlim -= 1
        if(pkg.hlim <= 0):return
    # send message
    print(f"{pkg.dst} -> {dstSock}")
    if(dstSock is not None):
        # "best" path
        try:
            dstSock.send(pkg.do_build())
            return
        except:
            # connection closed?
            redirectMap.pop(pkg.dst)
    for cnn in connections:
        if(cnn is blueServer):continue
        if(cnn is sock):continue
        try:
            cnn.send(pkg.do_build())
        except:pass

socketDataOverFlow = {}

def readDataFromSocket(socket):
    data = socketDataOverFlow.get(socket)
    data = data or b''
    try:
        if(data):
            outl,_1,_2 = select.select([socket],[],[],0)
            if(len(outl) == 0):return data
        return data + socket.recv(66000 - len(data))
    except Exception as error: 
        print(
        type(error).__name__,          # TypeError
        __file__,                  # /tmp/example.py
        error.__traceback__.tb_lineno,  # 2
        error
        )
    print('disconnected')
    connections.remove(socket)
    socket.close()
    return b''

sendMeSock4 = socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_RAW)
sendMeSock6 = socket.socket(socket.AF_INET6,socket.SOCK_RAW,socket.IPPROTO_RAW)
#sendMeSock4.connect((hereIp4,0))
#sendMeSock6.connect((hereIp6,0))
def sendMeDown(pkg):
    pkg = pkg.copy()
    print(f"getting IP: {pkg.dst} from {pkg.src}")
    # send to self
    # funny stuff
    pkg.dst = [hereIp4,hereIp6][(pkg.version - 4) // 2]
    #pkg.dst = [myIp4,myIp6][(pkg.version - 4) / 2]
    #outing = pkg.do_build()
    if(pkg.version == 4):
        sendMeSock4.sendto(pkg.do_build(),("127.0.0.1",0))
    if(pkg.version == 6):
        sendMeSock6.sendto(pkg.do_build(),("::1",0))
    #scapy.all.send(pkg)

def blueHandel(sock,connections):
    global running
    packetBase4 = scapy.all.IP()
    packetBase6 = scapy.all.IPv6()
    try:
        while True:
            # sleeping
            time.sleep(0.1)
            # important values
            cmpTime = time.time()
            defaultVec = (None,-timeToDeath,999)
            # what to read
            readable, writeable, exceptional = select.select(
                    connections,[],[],0.1)
            for s in readable:
                if s is blueServer:
                    connection, client_address = blueServer.accept()
                    print(f"{connection=} {client_address=}")
                    connection.setblocking(0)
                    connections.append(connection)
                    continue
                doContinueRead = True
                while doContinueRead:
                    doContinueRead = False
                    data = readDataFromSocket(s)
                    if(len(data) <= 0):
                        continue
                    if(data[0] >> 4 == 4):
                        pkg = packetBase4.__class__(data)
                        if(len(data) > pkg.len):
                            socketDataOverFlow[s] = data[pkg.len:]
                            doContinueRead = True
                        elif(len(data) < pkg.len):
                            print("NONNON")
                            socketDataOverFlow[s] = data
                            continue
                    elif(data[0] >> 4 == 6):
                        pkg = packetBase6.__class__(data)
                        if(len(data) > pkg.plen + 40):
                            socketDataOverFlow[s] = data[pkg.plen + 40:]
                            doContinueRead = True
                        elif(len(data) < pkg.plen + 40):
                            print("NONNON")
                            socketDataOverFlow[s] = data
                            continue
                    else:print(data);continue
                    if(pkg.dst == myIp4 or pkg.dst == myIp6):
                        sendMeDown(pkg)
                        dstSock = bindIpSocket(pkg,defaultVec,cmpTime,s)
                        #XXX """
                        continue
                    if(pkg.dst == broadIp4 or pkg.dst == broadIp6):
                        sendMeDown(pkg)
                        dstSock = None # broadcast
                    else:
                        # find best connection...
                        dstSock = bindIpSocket(pkg,defaultVec,cmpTime,s)
                    print(f"passing IP: {pkg.src} -> {pkg.dst} - of {s}")
                    trySendPacket(pkg,dstSock)
            while len(messageQueue) > 0:
                pkg = messageQueue.pop(0)
                print(f"Destination IP: {pkg.dst}")
                # find best connection...
                dstSock = bindIpSocket(pkg,defaultVec,cmpTime)
                trySendPacket(pkg,dstSock)
            if(not running):
                break

        # end of while
    except Exception as error:
        # error out
        while running:running = False;time.sleep(0.1)
        print(
        type(error).__name__,          # TypeError
        __file__,                  # /tmp/example.py
        error.__traceback__.tb_lineno,  # 2
        error
        )
    sendMeSock4.close()
    sendMeSock6.close()


def ipHandel(packet):
    # TODO make this dynamic!
    if scapy.all.IP in packet:
        ip_layer = packet[scapy.all.IP]
        if(ip_layer.dst.startswith(beginnIp4)):
            print(ip_layer)
            ip_layer.src = myIp4
            messageQueue.append(ip_layer)
            #messageQueue.append(packet)
    if scapy.all.IPv6 in packet:
        ip_layer = packet[scapy.all.IPv6]
        if(ip_layer.dst.startswith(beginnIp6)):
            ip_layer.src = myIp6
            messageQueue.append(ip_layer)
            #messageQueue.append(packet)


blueThread = threading.Thread(target=blueHandel, args=(blueServer,connections))
#sniffThread = threading.Thread(target=startIpHandel, args=(1,))
blueThread.start()
#sniffThread.start()
scapy.all.sniff(iface="veth0",prn=ipHandel, stop_filter=lambda p: not running)
while running:running = False;time.sleep(0.1)
blueThread.join()
if(config_data["doSetup"]):
    os.system('ip addr del 172.16.0.0/16 brd + dev veth0 label eth0:0')
    os.system('ip addr del 10::/10 dev veth0 label eth0:0')
    os.system('ip link delete veth0 type dummy')
    os.system('rmmod dummy')
    #os.system('ip route del 172.16.0.0/16')# via 172.17.0.1')
    #os.system('arp -d 172.17.0.1')
#sniffThread.join()
#rawSock.send()

blueServer.close()
for con in connections:
    con.close()


