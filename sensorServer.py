import time
from flask import Flask, jsonify
import board
import adafruit_bme280

# Initialisiere den BME280-Sensor über I2C
i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x77)  # Ändere auf 0x76 falls nötig

# Flask-App initialisieren
app = Flask(__name__)

def read_sensor():
    """Liest Sensordaten."""
    try:
        temperature = bme280.temperature
        humidity = bme280.humidity
        pressure = bme280.pressure
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"Sensordaten: Temp={temperature:.2f}°C, Feuchte={humidity:.2f}%, Druck={pressure:.2f}hPa")
        return {
            'temperature': temperature,
            'humidity': humidity,
            'pressure': pressure,
            'timestamp': timestamp
        }
    except Exception as e:
        print(f"Fehler: {e}")
        return {'temperature': -999, 'humidity': -999, 'pressure': -999, 'timestamp': 'Fehler'}

@app.route('/data')
def get_data():
    """API-Endpunkt: Gibt Sensordaten als JSON zurück."""
    data = read_sensor()
    return jsonify(data)

if __name__ == '__main__':
    print("Starte Pi-Sensor-Server auf Port 5001...")
    print("API verfügbar unter: http://<DEINE_PI_IP>:5001/data")
    app.run(host='0.0.0.0', port=5001, debug=True)
