import time
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

def compressFiles(fileNames=[]):
    count = 0
    for file in fileNames:
        print("Compressing file", file)
        if(not file.startswith("temp")):continue
        if(not file.endswith(".data")):continue
        count += 1
        # could also put this into xz
        with open(WEATHERDATA_FILE + file,"rb") as fptr:
            outp = fptr.read()
        with lzma.open(WEATHERDATA_FILE + file[:-5],"a")as fptr:
            fptr.write(outp)
            fptr.flush()
        os.remove(WEATHERDATA_FILE + file)
    print(f"Compressed: {count} Files")


def fetch_data_from_pis(interval = 5):
    # TODO add dating to file-name
    strfTime = datetime.datetime.now().strftime("temp-%Y-%m-%d");
    fptr = open(WEATHERDATA_FILE + f"{strfTime}.data","ab")
    lastMin = ""
    currentMin = ""
    minuteData = {}
    exiting = False
    cpAddresses = []
    while True:
        for ipAddr,piname in cpAddresses:
            if(type(piname) == bytes):
                piname = str(piname,"utf-8")
                piname = piname.split("\n")[0]
            try:
                url = f'http://{ipAddr}:{PORT}'
                response = requests.get(url, timeout=5)#,max_retries=1)
                if response.status_code == 200:
                    data = response.json()[0]
                    data["name"] = piname
                    sensor_data[piname] = data
                    minuteData[piname] = data
                    currentMin = data["timestamp"][:-3]
                else: print(f"Fehler bei Pi{i} ({ip}): Status {response.status_code}")
            except Exception as e:
                print(f"Verbindungsfehler zu Pi-{piname} ({ipAddr}): {e}")
        if(lastMin == ""):lastMin = currentMin
        if(currentMin != lastMin):
            print(lastMin,minuteData)
            strfTime2 = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M ");
            fptr.write(bytes(strfTime2,"utf-8"))
            isFirst = True
            for name,val in minuteData.items():
                naming = val["name"]
                naming = naming.replace(" ","").replace('"',"").replace("'","")
                naming = naming.replace(",","")
                if(isFirst):
                    outp = ""
                    isFirst = False
                else:outp = " "
                outp += f'n:{naming},'
                outp += f't:{val["temperature"]:.2f},'
                outp += f'h:{val["humidity"]:.2f},'
                outp += f'p:{val["pressure"]:.2f}'
                fptr.write(bytes(outp,"utf-8"))
            fptr.write(b"\n")
            if(lastMin[-1] == "0"):
                fptr.flush()
                os.fsync(fptr)
            minuteData.clear()
            lastMin = currentMin
            strfTime2 = datetime.datetime.now().strftime("temp-%Y-%m-%d");
            if(strfTime != strfTime2):
                fptr.flush()
                fptr.close()
                strfTime = strfTime2
                # start the compression thread
                listing = os.listdir(WEATHERDATE_FILE)
                th = Thread(target=compressFiles,args=(listing,))
                th.start()
                fptr = open(WEATHERDATA_FILE + f"{strfTime}.data","ab")

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
    listing = os.listdir(WEATHERDATE_FILE)
    # start the compression thread
    th = Thread(target=compressFiles,args=(listing,))
    th.start()
    print("StoppFetch")



