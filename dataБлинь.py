
import socket
import select
import time
import json

def getConnections(name=b"name",addr="172.31.255.255",port=2048):
    if(":" in addr):
        udp = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)
    else:
        udp = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        udp.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    udp.sendto(name,(addr,port))
    time.sleep(2)
    outp = []
    while True:
        readable, writeable, exceptional = select.select(
                [udp],[],[],0.1)
        if(len(readable) == 0):break
        for s in readable:
            otp = udp.recvfrom(1024)
            print(otp)
            outp.append(otp)
    udp.close()
    return outp

def getDataTCP(name=b"{}",addr="172.16.0.0",port=2680):
    if(":" in addr):
        tcp = socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
    else:
        tcp = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        tcp.connect((addr,port))
    except:return None
    tcp.send(name)
    time.sleep(2)
    outp = b""
    while True:
        readable, writeable, exceptional = select.select(
                [tcp],[],[],0.1)
        if(len(readable) == 0):break
        for s in readable:
            outp += s.recv(1024)
    tcp.close()
    return outp

def main():
    gatherData = b'{"count":99999}'
    while True:
        connections = getConnections(b"hi","172.31.255.255",2048)
        for name,(hAddr,hPort) in connections:
            got = getDataTCP(gatherData,addr=hAddr,port=2680)
            if(got is None):continue
            try:jData = json.loads(str(got,"utf-8"))
            except:continue
            print(name,jData[0])
            print(name,jData[-1])
            print(name,jData[0]["timestamp"],jData[-1]["timestamp"])
            dTemp = jData[0]["temperature"]
            dPres = jData[0]["pressure"]
            dHumi = jData[0]["humidity"]
            dTemp -= jData[-1]["temperature"]
            dPres -= jData[-1]["pressure"]
            dHumi -= jData[-1]["humidity"]
            print(f"  {'-' if dTemp < 0 else '+'} {dTemp if dTemp > 0 else -dTemp:.2f} °C")
            print(f"  {'-' if dHumi < 0 else '+'} {dHumi if dHumi > 0 else -dHumi:.2f} %rH")
            print(f"  {'-' if dPres < 0 else '+'} {dPres if dPres > 0 else -dPres:.2f} hPa")
            print(f"prediction:")
            print(f"  {jData[0]['temperature'] + dTemp:.2f} °C")
            print(f"  {jData[0]['pressure'] + dPres:.2f} hPa")
            print(f"  {jData[0]['humidity'] + dHumi:.2f} %rH")
            if(dPres < -1):print("Luftdruck sinkt extrem")
            elif(dPres < -0.1):print("Luftdruck sinkt")
            elif(dPres < -0):print("Luftdruck sinkt leicht")
            elif(dPres > 1):print("Luftdruck steigt extrem")
            elif(dPres > 0.1):print("Luftdruck steigt")
            elif(dPres > 0):print("Luftdruck steigt leicht")
        try:
            time.sleep(64)
        except:
            break

if __name__ == "__main__":
    main()
