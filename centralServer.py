import time
import requests
from flask import Flask, render_template_string
from threading import Timer

app = Flask(__name__)

# RaspyIP!!!
PI_IPS = ['172.28.37.102', '172.18.99.160']  
PORT = 2680  

sensor_data = {
    'pi1': {'temperature': 0.0, 'humidity': 0.0, 'pressure': 0.0, 'timestamp': ''},
    'pi2': {'temperature': 0.0, 'humidity': 0.0, 'pressure': 0.0, 'timestamp': ''}
}

# pre fetch html
with open("WetterWeb.html") as fptr:
    html_template = fptr.read()

def fetch_data_from_pis():
    for i, ip in enumerate(PI_IPS, 1):
        try:
            url = f'http://{ip}:{PORT}/data'
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()[0]
                sensor_data[f'pi{i}'] = data
                print(f"Daten von Pi{i} ({ip}) geholt: Temp={data['temperature']:.2f}°C")
            else:
                print(f"Fehler bei Pi{i} ({ip}): Status {response.status_code}")
                sensor_data[f'pi{i}'] = {'temperature': -999, 'humidity': -999, 'pressure': -999, 'timestamp': 'Verbindung fehlgeschlagen'}
        except Exception as e:
            print(f"Verbindungsfehler zu Pi{i} ({ip}): {e}")
            sensor_data[f'pi{i}'] = {'temperature': -999, 'humidity': -999, 'pressure': -999, 'timestamp': 'Verbindung fehlgeschlagen'}
    
    #reset nach 5sek (?)
    Timer(5.0, fetch_data_from_pis).start() #!!!

@app.route('/')
def index():
    return render_template_string(html_template,
        pi1_temperature=sensor_data['pi1']['temperature'],
        pi1_humidity=sensor_data['pi1']['humidity'],
        pi1_pressure=sensor_data['pi1']['pressure'],
        pi1_timestamp=sensor_data['pi1']['timestamp'],
        pi2_temperature=sensor_data['pi2']['temperature'],
        pi2_humidity=sensor_data['pi2']['humidity'],
        pi2_pressure=sensor_data['pi2']['pressure'],
        pi2_timestamp=sensor_data['pi2']['timestamp']
    )

if __name__ == '__main__':
    print("starte zentralen Server auf Port 5000")
    print("öffne im Browser: http://<IP HIER>:5000")
    print("bitte IPs in PI_IPS anpassen")
    # Starte ersten Datenabruf
    fetch_data_from_pis()
    # Starte Server
    app.run(host='0.0.0.0', port=5000, debug=True)
