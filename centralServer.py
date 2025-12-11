import time
import os
import requests
from flask import Flask, render_template_string, render_template, Response
from flask_socketio import SocketIO, send, emit, join_room, leave_room

from threading import Timer, Lock, Thread
import select
import socket
import json
import re
try:
    import lzma
except:
    pass

app = Flask(__name__)
appSocket = SocketIO(app)

# RaspyIP
mutex = Lock()
running = True

reqAddresses = []
#reqAddresses = [("127.0.0.1","me")] # uncomment, 4 debugging!
reqSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
reqSocket.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
PORT = 2680  
WEATHERDATA_FILE = "." + os.sep + "temp" + os.sep
HTML_DEFAULT_PATH = "." + os.sep + "htmlSeiten" + os.sep

if("sensor_data" not in globals()):
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



def fetch_data_from_pis(interval = 5):
    # TODO add dating to file-name
    try:
        fptr = lzma.open(WEATHERDATA_FILE + "temp.xz","a")
    except:
        fptr = open(WEATHERDATA_FILE + "temp.data","ab")
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
            fptr.write(bytes(lastMin + " ","utf-8"))
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
                outp += f'p:{val["pressure"]:.1f}'
                fptr.write(bytes(outp,"utf-8"))
            fptr.write(b"\n")
            if(lastMin[-1] == "0" or lastMin[-1] == "5"):
                os.fsync(fptr)
            minuteData.clear()
            lastMin = currentMin
            fptr.flush()

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
    fptr.close()
    print("StoppFetch")


def sanitise(filename):
    keepcharacters = ('.','_')
    return "".join(c for c in filename if c.isalnum() or c in keepcharacters).rstrip()

def getFromData(string):
    outp = []
    lines = string.split("\n")
    for ln in lines:
        spaces = ln.split(" ")
        time = spaces[0]
        if(not re.match("\d\d(\d\d[-_]){4}\d\d",time)):
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

@app.route('/data/<fileName>')
def get_WetterData(fileName):
    fileName = sanitise(fileName)
    try:
        if(len(fileName) in [0,1]):
            outp = os.listdir(WEATHERDATA_FILE)
        elif(fileName.endswith(".data")):
            with open(WEATHERDATA_FILE + fileName,"r")as fptr:
                outp = fptr.read()
            outp = getFromData(outp)
        else:
            with lzma.open(WEATHERDATA_FILE + fileName,"r") as fptr:
                outp = str(fptr.read(),"utf-8")
            outp = getFromData(outp)
        return Response(json.dumps(outp),mimetype="application/json")
    except Exception as error:
        e = (type(error).__name__+"\n"+          # TypeError
        __file__+"\n"+                  # /tmp/example.py
        error.__traceback__.tb_lineno+"\n"+  # 2
        error)

        return Response(str(e),mimetype="application/json")


@app.route('/file/<fileName>')
def get_style_css(fileName):
    ext = fileName.split(".")[-1]
    extList = {
            "gif":"image/gif","ico":"image/vnd.microsoft.icon", "mp3":"audio/mpeg","mp4":"video/mp4",
            "css":"text/css", "json":"application/json","md":"text/markdown","js":"text/javascript",
            "txt":"text/plain","data":"text/plain","html":"text/html","htm":"text/html"}
    if(extList.get(ext) != None):
        ext = extList[ext]
    else:
        ext = "text/html"
    fileName = sanitise(fileName)
    with open(HTML_DEFAULT_PATH + fileName,"r") as fptr:
        data = fptr.read()
    return Response(data,mimetype=ext)

@app.route('/wetterWeb')
def WetterWeb_site():
    table_row = ""
    sdata = sensor_data
    for key,val in sdata.items():
        table_row += f"<tr class=\"pi-data\">"
        table_row += f"<td>{key}</td>"
        table_row += f"<td>{val['temperature']:.2f}</td>"
        table_row += f"<td>{val['humidity']:.2f}</td>"
        table_row += f"<td>{val['pressure']:.2f}</td>"
        table_row += f"<td>{val['timestamp']}</td>"

        table_row += f"</tr>"

    htmlData = ""
    with open(HTML_DEFAULT_PATH + "WetterWeb.html","r")as fptr:
        htmlData = fptr.read()
    htmlData = htmlData.replace("$$$",table_row)

    return render_template_string(htmlData,
      #HerePis=herePis,
      #pi_temperature=pi_temp,
      #pi_humidity=pi_hum,
      #pi_pressure=pi_pres,
      #pi_timestamp=pi_time
    )

@appSocket.on("getWeatherNow")
def socket_GetWeatherNow(data):
    emit("setWeatherNow",json.dumps(sensor_data))

@appSocket.on("fetchWeather")
def socket_GetWeatherNow(data):
    length = 1024 # last 1024 bytes?
    start = -1 # (end)
    fmt = "raw"
    file = "temp.data"
    try:
        jsData = json.loads(data)
        length = int(jsData["length"])
        start = int(jsData["start"])
        fmt = jsData["fmt"]
        file = sanitise(jsData["file"])
    except:pass
    with open(WEATHERDATA_FILE + file,"r")as fptr:
        maxima = fptr.seek(0,2) # seek(0,end)
        if(length == -1):length = maxima
        if(start == -1):fptr.seek(maxima - length)
        outp = fptr.read(length)
    if(fmt == "json"):
        outp = json.dumps(getFromData(outp))
    emit("sendWeather",outp)

@app.route("/graph")
def graphen():
    with open(HTML_DEFAULT_PATH + "graphen.html","r")as fptr:
        htmlData = fptr.read()
    return render_template_string(htmlData)

@app.route("/winSim3000")
def winSim3000():
    with open(HTML_DEFAULT_PATH + "winSim3000.html","r")as fptr:
        htmlData = fptr.read()
    return render_template_string(htmlData)
@app.route("/")
def index():
    htmlData = "XXX"
    with open(HTML_DEFAULT_PATH + "index.html","r")as fptr:
        htmlData = fptr.read()
    
    return render_template_string(htmlData,
    )

if __name__ == '__main__':
    print("starte zentralen Server auf Port 5000")
    print("öffne im Browser: http://<IP HIER>:5000")
    # worker threads
    timFetch = Thread(target=fetch_data_from_pis,args=(5,))
    timGetPi = Thread(target=get_pi_addresses,args=(60,))
    timFetch.start()
    timGetPi.start()
    # Starte Server
    #requires pyopenssl
    app.use_reloader = False # making data gathering work...
    app.run(host='0.0.0.0', port=5000, ssl_context="adhoc")
    print(timFetch.is_alive())
    print(timGetPi.is_alive())
    with mutex:
        while(running):
            running = False;time.sleep(0.1)
    timFetch.join()
    timGetPi.join()
    print()
