import time
import os
from flask import Flask, render_template_string, render_template, Response
from flask_socketio import SocketIO, send, emit, join_room, leave_room

from threading import Timer, Lock, Thread
import json
import re
import raspiHandler
try:
    import lzma
except:
    pass

app = Flask(__name__)
appSocket = SocketIO(app)

# RaspyIP
running = True
mutex = raspiHandler.mutex

WEATHERDATA_FILE = "." + os.sep + "temp" + os.sep
HTML_DEFAULT_PATH = "." + os.sep + "htmlSeiten" + os.sep

if("sensor_data" not in globals()):
    sensor_data = {}
    raspiHandler.sensor_data = sensor_data


def sanitise(filename):
    keepcharacters = ('.','_','-')
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
    timFetch = Thread(target=raspiHandler.fetch_data_from_pis,args=(5,))
    timGetPi = Thread(target=raspiHandler.get_pi_addresses,args=(60,))
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
            raspiHandler.running = False
    timFetch.join()
    timGetPi.join()
    print()
