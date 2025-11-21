import time
import requests
from flask import Flask, render_template_string, render_template, Response
from threading import Timer, Lock, Thread
import select
import socket

app = Flask(__name__)

# RaspyIP
mutex = Lock()
running = True

reqAddresses = []
reqSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
reqSocket.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
PORT = 2680  

sensor_data = {
}


def get_pi_addresses(interval = 60):
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
            if(not running):break
        print("updated pis")
        #time.sleep(interval)
        for _ in range(interval):
            time.sleep(1)
            if(not running):break
    print("StoppGet")

def fetch_data_from_pis(interval = 5):
    cpAddresses = []
    while True:
        for ipAddr,piname in cpAddresses:
            try:
                url = f'http://{ipAddr}:{PORT}'
                response = requests.get(url, timeout=5)#,max_retries=1)
                if response.status_code == 200:
                    data = response.json()[0]
                    sensor_data[piname] = data
                    print(f"Daten von Pi-{piname} ({ipAddr}) geholt: Temp={data['temperature']:.2f}°C")
                else:
                    print(f"Fehler bei Pi{i} ({ip}): Status {response.status_code}")
                    #sensor_data[f'pi{i}'] = {'temperature': -999, 'humidity': -999, 'pressure': -999, 'timestamp': 'Verbindung fehlgeschlagen'}
            except Exception as e:
                print(f"Verbindungsfehler zu Pi-{piname} ({ipAddr}): {e}")
                #sensor_data[f'pi{i}'] = {'temperature': -999, 'humidity': -999, 'pressure': -999, 'timestamp': 'Verbindung fehlgeschlagen'}
        with mutex:
            cpAddresses = reqAddresses
            if(not running):break
        #time.sleep(interval)
        for _ in range(interval):
            time.sleep(1)
            if(not running):break
    print("StoppFetch")

@app.route('/file/<fileName>')
def get_style_css(fileName):
    if(".." in fileName):
        return Respnse("No!")
    with open(fileName,"r") as fptr:
        data = fptr.read()
    return Response(data,mimetype="text/css")

@app.route('/WetterWeb')
def WetterWeb_site():
    #herePis = ""
    #pi_temp = ""
    #pi_hum = ""
    #pi_pres = ""
    #pi_time = ""
    table_row = ""
    for key,val in sensor_data.items():
        #herePis += f"<th>{key}</th>"
        #pi_temp += f"<td>{val['temperature']}</td>"
        #pi_hum += f"<td>{val['humidity']}</td>"
        #pi_pres += f"<td>{val['pressure']}</td>"
        #pi_time += f"<td>{val['timestamp']}</td>"
        table_row += f"<tr class=\"pi-data\">"
        table_row += f"<td>{key}</td>"
        table_row += f"<td>{val['temperature']}</td>"
        table_row += f"<td>{val['humidity']}</td>"
        table_row += f"<td>{val['pressure']}</td>"
        table_row += f"<td>{val['timestamp']}</td>"

        table_row += f"</tr>"

    htmlData = ""
    with open("WetterWeb.html","r")as fptr:
        htmlData = fptr.read()
    htmlData = htmlData.replace("$$$",table_row)

    return render_template_string(htmlData,
      #HerePis=herePis,
      #pi_temperature=pi_temp,
      #pi_humidity=pi_hum,
      #pi_pressure=pi_pres,
      #pi_timestamp=pi_time
    )

@app.route("/")
def index():
    htmlData = "XXX"
    with open("index.html","r")as fptr:
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
    app.run(host='0.0.0.0', port=5000, debug=True)
    print(timFetch.is_alive())
    print(timGetPi.is_alive())
    with mutex:
        while(running):
            running = False;time.sleep(0.1)
    timFetch.join()
    timGetPi.join()
    print()
