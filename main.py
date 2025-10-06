
import bluetooth
import scapy.all
import json
import select
import time
import threading
import random


CONFIG_FILE = "./config.json"
with open(CONFIG_FILE,"r") as fptr:
    config_data = json.load(fptr)

# maybe add plugins?

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

# listening (socket)

messageQueue = []
redirectMap = {} # this will be generated
# TODO add more features here
myIp4 = config_data.get("ip4") or "10.x.x.x"
myIp6 = config_data.get("ip6") or "10:x:x:x:x:x:x:x"
while("x" in myIp4):
    myIp4 = myIp4.replace("x",str(random.randrange(256)),1)
while("x" in myIp6):
    myIp6 = myIp6.replace("x",hex(random.randrange(0xffff))[2:],1)
print(f"currently using: {myIp4} , {myIp6} as addresses!")
running = True
timeToDeath = config_data.get("ttd") or 10

def trySendPacket(pkg,defaultVec,cmpTime,sock=None):
    del(pkg.chksum)
    # find best connection...
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
    if(dstTime < cmpTime - timeToDeath and dstSock is not None):
        # if too old!
        redirectMap.pop(pkg.dst)
        dstSock = None
    # send message
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
        try:
            cnn.send(pkg.do_build())
        except:pass
            

def readDataFromSocket(socket):
    data = b''
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
        error.__traceback__.tb_lineno,  # 2
        error
        )
    if data: print('received', buffer)
    else:
        print('disconnected')
        connections.remove(socket)
    return buffer

def blueHandel(sock,connections):
    global running
    packetBase4 = scapy.all.IP()
    packetBase6 = scapy.all.IPv6()
    try:
        while running:
            # sleeping
            time.sleep(0.1)
            # important values
            cmpTime = time.process_time()
            defaultVec = (None,-timeToDeath,999)
            # what to read
            readable, writeable, exceptional = select.select(
                    connections,[],connections,1)
            for s in readable:
                if s is blueServer:
                    connection, client_address = blueServer.accept()
                    print(f"{connection=} {client_address=}")
                    connection.setblocking(0)
                    connections.append(connection)
                    continue
                data = readDataFromSocket(s)
                if(len(data) <= 0):
                    continue
                if(data[0] >> 4 == 4):
                    pkg = packetBase4.__class__.fromBytearray(data)
                elif(data[0] >> 4 == 6):
                    pkg = packetBase6.__class__.fromBytearray(data)
                else:print(data);continue
                if(pkg.dst == myIp4 and pkg.dst != myIp6):
                    print(f"getting IP: {pkg.dst}")
                    # send to self
                    del(pkg.chksum)
                    # funny stuff
                    pkg.dst = ["127.0.0.1","::1"][(pkg.version - 4) / 2]
                    #pkg.dst = [myIp4,myIp6][(pkg.version - 4) / 2]
                    #outing = pkg.do_build()
                    scapy.all.send(pkg)
                    continue
                print(f"passing IP: {pkg.dst}")
                trySendPacket(pkg,defaultVec,cmpTime,s)
            if len(messageQueue) > 0:
                pkg = messageQueue.pop(0)
                print(f"Destination IP: {pkg.dst}")
                trySendPacket(pkg,defaultVec,cmpTime)

        # end of while
    except Exception as error:
        # error out
        running = False
        print(
        type(error).__name__,          # TypeError
        __file__,                  # /tmp/example.py
        error.__traceback__.tb_lineno,  # 2
        error
        )


def ipHandel(packet):
    if scapy.all.IP in packet:
        ip_layer = packet[scapy.all.IP]
        if(ip_layer.dst.startswith("10.")):
            packet.src = myIp4
            messageQueue.append(ip_layer)
            #messageQueue.append(packet)
    if scapy.all.IPv6 in packet:
        ip_layer = packet[scapy.all.IPv6]
        if(ip_layer.dst.startswith("10:")):
            packet.dst = myIp4
            messageQueue.append(ip_layer)
            #messageQueue.append(packet)

def startIpHandel(*_,**__):
    global running
    scapy.all.sniff(prn=ipHandel, stop_filter=lambda p: not running)
    running = False


blueThread = threading.Thread(target=blueHandel, args=(blueServer,connections))
sniffThread = threading.Thread(target=startIpHandel, args=(1,))
blueThread.start()
sniffThread.start()
try:
    while running: time.sleep(1)
except:pass
running = False
blueThread.join()
sniffThread.join()
#rawSock.send()

blueServer.close()
for con in connections:
    con.close()
