#!/usr/bin/env python3

import bluetooth
import scapy.all
import json
import select
import time
import datetime
import threading
import random
import socket
import os


CONFIG_FILE = "./config.json"
with open(CONFIG_FILE,"r") as fptr:
    config_data = json.load(fptr)

# listening (socket)

def printing(string):
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),string)

messageQueue = []
# (ip->(socket,timestamp,hops))
redirectMap = {} # this will be generated
# (ip->timestamp)
brdCastSleep = {} # this also

#ipv4
myIp4 = config_data.get("ip4") or "172.16.0.0/12"
valueIp4 = 0
for v in [int(x) for x in myIp4.split("/")[0].split(".")]:
    valueIp4 <<= 8
    valueIp4 += v
sub4 = 32 - int(myIp4.split("/")[1])
broadValue = valueIp4 | (1 << sub4) - 1
valueIp4 |= broadValue & random.randrange(1,(1 << sub4) - 1)
myIp4 = []
broadIp4 = []
sub4 = 32 - sub4
for _ in range(4):
    myIp4.insert(0,str(valueIp4 & 255))
    broadIp4.insert(0,str(broadValue & 255))
    valueIp4 >>= 8
    broadValue >>= 8
myIp4 = ".".join(myIp4)
broadIp4 = ".".join(broadIp4)

#ipv6
myIp6 = config_data.get("ip6") or "10::/16"
valueIp6 = 0
stringing6 = [(int(x,16) if x != "" else "") for x in myIp6.split("/")[0].split(":")]
if(stringing6[0] == ""):stringing6[0] = 0 # catch :12::1
if(stringing6[-1] == ""):stringing6[-1] = 0 # catch 10::1:
index6 = stringing6.index("")
stringing6.pop(index6)
while stringing6.count("") > 0: stringing6.pop(stringing6.index(""))
while len(stringing6) < 8: stringing6.insert(index6,0)
print(stringing6)
for v in stringing6:
    valueIp6 <<= 16
    valueIp6 += v
sub6 = 128 - int(myIp6.split("/")[1])
broadValue = valueIp6 | (1 << sub6) - 1
valueIp6 |= broadValue & random.randrange(1,(1 << sub6) - 1)
myIp6 = []
broadIp6 = []
sub6 = 128 - sub6
for _ in range(8):
    myIp6.insert(0,hex(valueIp6 & 0xffff)[2:])
    broadIp6.insert(0,hex(broadValue & 0xffff)[2:])
    valueIp6 >>= 16
    broadValue >>= 16
myIp6 = ":".join(myIp6)
broadIp6 = ":".join(broadIp6)

#
printing(f"lcl: {myIp4} , {myIp6}")
printing(f"brd: {broadIp4} , {broadIp6}")
running = True
timeToDeath = config_data.get("ttd") or 10
brdSleepTime = config_data.get("brdSleep") or 5
rescan_scale = config_data.get("rescanScale") or 30
messageLimit = config_data.get("messageLimit") or 30
runningMutex = threading.Lock()

if(config_data["doSetup"]):
    # adding virtual interface ...
    # https://linuxconfig.org/configuring-virtual-network-interfaces-in-linux
    os.system('modprobe dummy')
    os.system('ip link add veth0 type dummy') # void ethernet
    os.system('ip link show veth0') # testing if veth0 exists
    os.system('ifconfig veth0 hw ether 11:22:33:44:55:66') # testing if veth0 exists
    if(config_data["useIp4"]):
        os.system(f'ip addr add {myIp4}/{sub4} brd + dev veth0') # testing if veth0 exists
    os.system(f'ip addr add {myIp6}/{sub6} dev veth0') # testing if veth0 exists
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
if(config_data["acceptConnections"]):
    blueServer = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    blueServer.bind(("",bluetooth.PORT_ANY))
    blueServer.listen(8)

    port = blueServer.getsockname()[1]
    bluetooth.advertise_service(blueServer, "BlueRelay", service_id=uuid,
                                service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
                                profiles=[bluetooth.SERIAL_PORT_PROFILE]
                                )
    connections.append(blueServer)
    printing("started Server")


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
        printing(f"{pkg.src} -> {(sock,cmpTime,pkg.hops())}")
    """if(dstTime < cmpTime - timeToDeath and dstSock is not None):
        # if too old!
        redirectMap.pop(pkg.dst)
        dstSock = None
    # """
    return dstSock

def trySendPacket(pkg,dstSock=None,sock=None):
    # limit the number of hops!
    if(pkg.version == 4):
        pkg.ttl -= 1
        if(pkg.ttl <= 0):return
    elif(pkg.version == 6):
        pkg.hlim -= 1
        if(pkg.hlim <= 0):return
    """if ((pkg.dst == broadIp4 or pkg.dst == broadIp6) and
            brdCastSleep.get(pkg.src)):
        ttime = brdCastSleep[pkg.src]
        if(ttime + brdSleepTime > cmpTime):
            printing(f"ignored {pkg.src}")
            return # right after data = readDataFromSocket
    #"""
    # send message
    printing(f"{pkg.dst} -> {dstSock} ... {pkg.src}")
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
    if(data is not None):
        socketDataOverFlow.pop(socket)
    else:
        data = b''
    try:
        """if(data):
            outl,_1,_2 = select.select([socket],[],[],0)
            print(outl)
            if(len(outl) == 0):return data
        #"""
        return data + socket.recv(66000)
    except Exception as error: 
        print(
        type(error).__name__,          # TypeError
        __file__,                  # /tmp/example.py
        error.__traceback__.tb_lineno,  # 2
        error
        )
    printing('disconnected')
    connections.remove(socket)
    socket.close()
    return b''

sendMeSock4 = socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_RAW)
sendMeSock6 = socket.socket(socket.AF_INET6,socket.SOCK_RAW,socket.IPPROTO_RAW)
sendMeSock4.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
sendMeSock6.setsockopt(socket.IPPROTO_IPV6, socket.IP_HDRINCL, 1)
sendMeSock4.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST, 1)
sendMeSock6.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST, 1)
def sendMeDown(_pkg):
    pkg = _pkg.copy()
    #pkg.show2()
    #pkg = scapy.all.IP(_pkg.build())
    if(pkg.version == 4): del(pkg.chksum)# = None
    printing(f"getting IP: {pkg.dst} from {pkg.src}")
    try: del(pkg.payload.chksum)# = None
    except:pass
    # send to self
    # funny stuff
    #pkg.show2()
    #pkg.dst = [myIp4,myIp6][(pkg.version - 4) / 2]
    #outing = pkg.do_build()
    """try:
        tcpp = scapy.all.TCP(pkg.payload)
        port = tcpp.dport
    except:pass
    try:
        udpp = scapy.all.UDP(pkg.payload)
        port = udpp.dport
    except:pass # """
    port = 0
    try:
        if(pkg.version == 4):
            #sendMeSock4.sendto(pkg.do_build(),("127.0.0.1",port))
            sendMeSock4.sendto(pkg.do_build(),(pkg.dst,port))
        if(pkg.version == 6):
            #sendMeSock6.sendto(pkg.do_build(),("::1",port))
            sendMeSock6.sendto(pkg.do_build(),(pkg.dst,port))
    except Exception as error: 
        print(
        type(error).__name__,          # TypeError
        __file__,                  # /tmp/example.py
        error.__traceback__.tb_lineno,  # 2
        error
        )
    """
    if(pkg.version == 4 and pkg.proto == 17):
        udpp = pkg.getlayer(scapy.all.UDP)
        udpp.chksum = None
        npkg = scapy.all.IP(src=pkg.src,id=pkg.id,flags=pkg.flags,dst="127.0.0.1") / scapy.all.UDP(sport=udpp.sport,dport=udpp.dport) / udpp.payload
        #scapy.all.sendp(scapy.all.Ether()/npkg,iface="lo")
        sendMeSock4.sendto(npkg.build(),("127.0.0.1",port))
        sendMeSock4.sendto(pkg.build(),("127.0.0.1",port))
        npkg.show2()
    else:
        scapy.all.sendp(scapy.all.Ether()/pkg,iface="lo")
    # """

def blueHandel(sock,connections):
    global running
    try:
        iterator = redirectMap.items().__iter__()
        timeToRescan = 0
        while True:
            # important values
            cmpTime = time.time()
            defaultVec = (None,-timeToDeath,999)
            try:
                # removing unimportant values in the redirectMap
                # clean up
                gotIp,(sock,tstTime,hops) = iterator.__next__()
                if(tstTime < cmpTime - timeToDeath):
                    # remove old entrys
                    printing(f"removing {gotIp} {redirectMap.pop(gotIp)}")
            except (StopIteration,RuntimeError):
                iterator = redirectMap.items().__iter__()
            #sendDownPkgs = []
            # what to read
            readable, writeable, exceptional = select.select(
                    connections,[],[],0.1)
            for s in readable:
                if s is blueServer:
                    # allow others to connect
                    connection, client_address = blueServer.accept()
                    printing(f"{connection=} {client_address=}")
                    connection.setblocking(0)
                    connections.append(connection)
                    continue
                index = 0
                data = readDataFromSocket(s)
                while True:
                    # iter over packets
                    if(len(data) <= index):
                        break
                    if(data[0] >> 4 == 4):
                        pkg = scapy.all.IP(data[index:])
                        # test for packt cutoff
                        if(len(data) < pkg.len + index):
                            printing(f"NONNON {len(data)}<{pkg.len + index}:{pkg.len}")
                            socketDataOverFlow[s] = data[index:]
                            printing(data[index:])
                            break
                        index += pkg.len
                    elif(data[0] >> 4 == 6):
                        pkg = scapy.all.IPv6(data)
                        # test for packt cutoff
                        if(len(data) < pkg.plen + 40 + index):
                            printing("NONNON")
                            socketDataOverFlow[s] = data[index:]
                            break
                        index += pkg.plen + 40
                    else:printing(data);break # if false!
                    dstSock = bindIpSocket(pkg,defaultVec,cmpTime,s)
                    if(pkg.dst == myIp4 or pkg.dst == myIp6):
                        #sendDownPkgs.append(pkg)
                        sendMeDown(pkg)
                        continue
                    if(pkg.dst == broadIp4 or pkg.dst == broadIp6):
                        sendMeDown(pkg)
                        dstSock = None # broadcast
                    if(dstSock is None):
                        if(brdCastSleep.get(pkg.src)):
                            # broadcast flooding prevention
                            ttime = brdCastSleep[pkg.src]
                            if(ttime > cmpTime):
                                printing(f"ignored {pkg.src}")
                                continue # right after data = readDataFromSocket
                        brdCastSleep[pkg.src] = cmpTime + brdSleepTime
                    printing(f"passing IP: {pkg.src} -> {pkg.dst} - of {s}")
                    trySendPacket(pkg,dstSock,s)
                timeToRescan = cmpTime + rescan_scale * len(connections)
            # Host -> BlueNetwork
            messageCounter = 0
            while len(messageQueue) > 0 and messageCounter < messageLimit:
                messageCounter += 1
                pkg = messageQueue.pop(0)
                printing(f"Destination IP: {pkg.dst}")
                # find best connection...
                dstSock = bindIpSocket(pkg,defaultVec,cmpTime)
                trySendPacket(pkg,dstSock)
                timeToRescan = cmpTime + rescan_scale * len(connections)
            # auto connect to clients
            if(config_data["makeConnections"] and cmpTime > timeToRescan) or\
                    (timeToRescan == 0 and config_data["makeFirstConnections"]):
                printing("Nothing happend for a very long time!")
                printing("Now searching for more clients!")
                timeToRescan = cmpTime + rescan_scale * len(connections)
                services = bluetooth.find_service(uuid=uuid,address=None)
                printing(services)
                for serv in services:
                    port = serv["port"]
                    name = serv["name"]
                    host = serv["host"]
                    printing("Connecting to \"{}\" on {}".format(name, host))
                    sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                    try:
                        sock.connect((host, port))
                        connections.append(sock)
                    except Exception as error:
                        # error out
                        print(
                        type(error).__name__,          # TypeError
                        __file__,                  # /tmp/example.py
                        error.__traceback__.tb_lineno,  # 2
                        error
                        )
                printing(f"Next in: {rescan_scale * len(connections)}s")
            with runningMutex:
                if(not running):break

        # end of while
    except Exception as error:
        # error out
        with runningMutex:
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
    # TODO don't accept unfinished packets
    if scapy.all.IP in packet:
        ip_layer = packet[scapy.all.IP]
        if len(ip_layer.build()) != ip_layer.len:
            printing(f"(2025-10-19T12:20:41){ip_layer}")
            return
        """if(ip_layer.dst.startswith(beginnIp4)):
            ip_layer.src = myIp4 # is this even used
            messageQueue.append(ip_layer)
            #messageQueue.append(packet)
        # """
        if ip_layer.src == myIp4:
            messageQueue.append(ip_layer)
        else:
            printing(f"(2025-10-30T18:34:34){ip_layer}")
    if scapy.all.IPv6 in packet:
        ip_layer = packet[scapy.all.IPv6]
        if len(ip_layer.build()) != ip_layer.plen:
            printing(f"(2025-10-19T12:20:50){ip_layer}")
            return
        """if(ip_layer.dst.startswith(beginnIp6)):
            ip_layer.src = myIp6
            messageQueue.append(ip_layer)
            #messageQueue.append(packet)
        # """
        if ip_layer.src == myIp6:
            messageQueue.append(ip_layer)
        else:
            printing(f"(2025-10-30T18:34:21){ip_layer}")

def handleReplyService():
    global running
    replySocket = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)
    replySocket.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    try:
        replyServicePort = config_data["replyService"]
        replySocket.bind(("",replyServicePort))
        hostReply = config_data["hostReply"]
        if("/" in hostReply and os.path.exists(hostReply)):
            with open(hostReply,"rb") as fptr:
                hostReply = fptr.read()
        else:hostReply = bytes(hostReply,"utf-8")
        while True:
            readable, writeable, exceptional = select.select(
                    [replySocket],[],[],1)
            for s in readable:
                data, addr = s.recvfrom(1024)
                s.sendto(hostReply,addr)
            with runningMutex:
                if(not running):
                    break
    except Exception as error: 
        print(
        type(error).__name__,          # TypeError
        __file__,                  # /tmp/example.py
        error.__traceback__.tb_lineno,  # 2
        error
        )
    replySocket.close()
    with runningMutex:
        while running:
            running = False;time.sleep(0.1) # set running false!

blueThread = threading.Thread(target=blueHandel, args=(blueServer,connections))
replyThread = threading.Thread(target=handleReplyService)
#sniffThread = threading.Thread(target=startIpHandel, args=(1,))
blueThread.start()
replyThread.start()
#sniffThread.start()
scapy.all.sniff(iface="veth0",prn=ipHandel, stop_filter=lambda p: not running)
with runningMutex:
    while running:
        running = False;time.sleep(0.1) # set running false!
blueThread.join()
if(config_data["doSetup"]):
    os.system('ip addr del 172.16.0.0/16 brd + dev veth0')
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


