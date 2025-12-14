import time
import re
import requests
import datetime
import os
from threading import Timer, Lock, Thread
import select
import socket
try:
    import lzma
except:pass

reqAddresses = []
#reqAddresses = [("127.0.0.1","me")] # uncomment, 4 debugging!
reqSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
reqSocket.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
WEATHERDATA_FILE = "." + os.sep + "temp" + os.sep
PORT = 2680  
mutex = Lock()
running = True
sensor_data = {}

def getFromData(string):
    outp = []
    lines = string.split("\n")
    for ln in lines:
        spaces = ln.split(" ")
        time = spaces[0]
        if(not re.match(r"\d\d(\d\d[-_]){4}\d\d",time)):
            continue
        spaces = spaces[1:]
        try:
            upDic = dict()
            for sp in spaces:
                dic = dict()
                dic["timestamp"] = time +"-00"
                parts = sp.split(",")
                dic["name"] = parts[0][2:]
                dic["temperature"] = parts[1][2:]
                dic["humidity"] = parts[2][2:]
                dic["pressure"] = parts[3][2:]
                upDic[dic["name"]] = dic
            outp.append(upDic)
        except:
            # if an extra timestamp is stored
            # or to catch any other error!
            pass
    return outp

def get_pi_addresses(interval = 60):
    exiting = False
    if(len(reqAddresses) != 0):
        return
    #global reqAddresses
    while True:
        print("reload pis")
        reqSocket.sendto(b"Hello",("172.31.255.255",2048))
        time.sleep(1)
        newAddresses = []
        ignoreList = []
        while True:
            readable,writeable,extra = select.select([reqSocket],[],[],1)
            if(len(readable) == 0):break
            for s in readable:
                name,otro = s.recvfrom(1024)
                print(name,otro)
                address,port = otro
                if(address in ignoreList):
                    continue
                newAddresses.append((address,name))
                ignoreList.append(address)
        with mutex:
            reqAddresses.clear()
            reqAddresses.extend(newAddresses)
            #reqAddresses = newAddresses
            if(not running):
                exiting = True
                break
        print("updated pis")
        #time.sleep(interval)
        for _ in range(interval):
            time.sleep(1)
            if(not running):
                exiting = True
                break
        if(exiting):break
    print("StoppGet")


def put_data_into_file(fptr,minuteData,currentMin):
    fptr.write(bytes(currentMin,"utf-8"))
    isFirst = True
    for name,val in minuteData.items():
        naming = val["name"]
        naming = naming.replace(" ","").replace('"',"").replace("'","")
        naming = naming.replace(",","")
        outp = " "
        outp += f'n:{naming},'
        outp += f't:{val["temperature"]:.2f},'
        outp += f'h:{val["humidity"]:.2f},'
        outp += f'p:{val["pressure"]:.2f}'
        fptr.write(bytes(outp,"utf-8"))
    fptr.write(b"\n")
    if(hash(currentMin) % 17 == 0):
        fptr.flush()
        os.fsync(fptr)

def fetch_data_from_pis(interval = 5):
    # TODO add dating to file-name
    strfTime = datetime.datetime.now().strftime("temp-%Y-%m-%d");
    fptr = lzma.open(WEATHERDATA_FILE + f"{strfTime}.xz","ab")
    lastMin = ""
    currentMin = ""
    minuteData = {}
    exiting = False
    cpAddresses = []
    hasData = False
    while True:
        for ipAddr,piname in cpAddresses:
            if(type(piname) == bytes):
                piname = str(piname,"utf-8")
                piname = piname.split("\n")[0]
            try:
                url = f'http://{ipAddr}:{PORT}'
                response = requests.get(url, timeout=5)#,max_retries=1)
                if response.status_code == 200:
                    hasData = True
                    data = response.json()[0]
                    data["name"] = piname
                    sensor_data[piname] = data
                    minuteData[piname] = data
                else: print(f"Fehler bei Pi{i} ({ip}): Status {response.status_code}")
            except Exception as e:
                print(f"Verbindungsfehler zu Pi-{piname} ({ipAddr}): {e}")
        currentMin = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M");
        if(lastMin == ""):lastMin = currentMin
        if(currentMin != lastMin and hasData):
            hasData = False
            put_data_into_file(fptr,minuteData,currentMin)

            minuteData.clear()
            lastMin = currentMin
            strfTime2 = datetime.datetime.now().strftime("temp-%Y-%m-%d");
            if(strfTime != strfTime2):
                fptr.flush()
                fptr.close()
                strfTime = strfTime2
                fptr = lzma.open(WEATHERDATA_FILE + f"{strfTime}.xz","ab")

        with mutex:
            cpAddresses = reqAddresses
            if(not running):
                exiting = True
                break
        #time.sleep(interval)
        for _ in range(interval):
            time.sleep(1)
            if(not running):
                exiting = True
                break
        if(exiting):break
    fptr.flush()
    fptr.close()
    print("StoppFetch")



# RaspyIP

if __name__ == '__main__':
    # worker threads
    timFetch = Thread(target=fetch_data_from_pis,args=(5,))
    timGetPi = Thread(target=get_pi_addresses,args=(60,))
    timFetch.start()
    timGetPi.start()
    # Starte Server
    try:
        while True:
            time.sleep(1)
    except:pass
    with mutex:
        while (running):
            running = False;time.sleep(0.1)
    print(timFetch.is_alive())
    print(timGetPi.is_alive())
    timFetch.join()
    timGetPi.join()
    print()
