#!/usr/bin/env python3

useNormal = True
import time
import socket
import threading
import json
import select
try:
    import bme280
    import smbus2
except:
    import random
    import datetime
    print("You do bad stuff!")
    useNormal = False

dateFormat = '%Y-%m-%d_%H-%M-%S'

# threading stuff
running = True
runningMutex = threading.Lock()
# sensor data
backlog = []
backlogLength = 256
backlogInterval = 5 # every 5 seconds
def readingSensor():
    global running
    port = 1
    address = 0x77 # Adafruit BME280 address. Other BME280s may be different
    if(useNormal):
        bus = smbus2.SMBus(port)
        bme280.load_calibration_params(bus,address)
    else:pass
    try:
        while True:
            if(useNormal):
                bme280_data = bme280.sample(bus,address)
                timestamp = str(bme280_data.timestamp)
                humidity  = bme280_data.humidity
                pressure  = bme280_data.pressure
                temperature = bme280_data.temperature
            else:
                humidity  = random.uniform(0,100)
                pressure  = random.uniform(900,1200)
                timestamp = datetime.datetime.now().strftime(dateFormat)
                temperature = random.uniform(19,25)
            #print(f"{timestamp}  {humidity}% rH  {pressure} hPa  {temperature} °C")
            with runningMutex:
                backlog.append({
                    #"name":socket.gethostname(),
                    "timestamp":timestamp,
                    "humidity":humidity,
                    "pressure":pressure,
                    "temperature":temperature
                    })
                if(len(backlog) > backlogLength):
                    backlog.pop(0)
                # end of loop
                if(not running):break
            time.sleep(backlogInterval)
    except KeyboardInterrupt:
        print("Stopping")
    except Exception as error: 
        print(
        type(error).__name__,          # TypeError
        __file__,                  # /tmp/example.py
        error.__traceback__.tb_lineno,  # 2
        error
        )
    with runningMutex:
        while(running):running = False

backlogThread = threading.Thread(target=readingSensor)
backlogThread.start()

# server part

def subsection(jdata):
    lowTime = 0
    highTime = 0
    count = 1
    adding = []
    try:
        if(jdata.get("lowGetTime")):
            lowTime = datetime.datetime.strptime(jdata["lowGetTime"], dateFormat)
        if(jdata.get("highGetTime")):
            highTime = datetime.datetime.strptime(jdata["highGetTime"], dateFormat)
        if(jdata.get("count")):
            count = int(jdata["count"])
        print(f"{lowTime=} {highTime=} {count=}")
        for v in range(len(backlog)-1,-1,-1):
            if(lowTime != 0 and lowTime > datetime.datetime.strptime(
                backlog[v]["timestamp"],dateFormat)):
               continue
            if(highTime != 0 and highTime < datetime.datetime.strptime(
                backlog[v]["timestamp"],dateFormat)):
               continue

            adding.append(backlog[v])
            if(len(adding) >= count):
                break
    except Exception as e:
        print(e)
        adding = [backlog[-1]]
    return adding

def httpParser(data):
    rpart = data.split(" ")[1].split("?")[-1]
    build = {}
    key = ""
    value = ""
    for chr in rpart:
        if(chr == '='):
            key = value
            value = ""
        elif(chr == '&'):
            build[key] = value
            try:build[key] = int(value)
            except:pass
            value = ""
            key = ""
        else:
            value += chr
    if(key != ""):
        build[key] = value
        try:build[key] = int(value)
        except:pass

    return build

tcpServer = socket.socket(socket.AF_INET6,socket.SOCK_STREAM)
udpServer = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)
tcpServer.bind(("",2680))
tcpServer.listen(5)
udpServer.bind(("",2680))
clients = [tcpServer,udpServer]
try:
    while True:
        readable, writeable, exceptional = select.select(
                clients,[],[],0.1)
        for s in readable:
            if s is tcpServer:
                # allow others to connect
                connection, client_address = s.accept()
                print(f"{connection=} {client_address=}")
                connection.setblocking(0)
                clients.append(connection)
                continue
            if s is udpServer:
                data,addr = s.recvfrom(128)
                print(data,addr)
                try:jdata = json.loads(data.decode("utf-8").replace("'",'"'))
                except:jdata = {}
                scraped = json.dumps(subsection(jdata))
                s.sendto(bytes(scraped,"utf-8"),addr)
                continue
            isHttp = False
            try:
                data = s.recv(2048)
            except BrokenPipeError:
                clients.remove(s)
                s.close()
                continue
            try:data = data.decode("utf-8")
            except:continue
            isHttp = data.startswith("GET")
            # do stuff for HTTP
            try:
                if(not isHttp):
                    jdata = json.loads(data.replace("'",'"'))
                else:
                    jdata = httpParser(data)
            except:jdata = {}
            scraped = json.dumps(subsection(jdata))
            try:
                if(not isHttp):
                    s.send(bytes(scraped,"utf-8"))
                    continue
                s.send(bytes("HTTP/1.1 200 \nContent-Type: application/json\n\n" + scraped,"utf-8"))
                clients.remove(s)
                s.shutdown(socket.SHUT_RDWR)
                continue
            except (BrokenPipeError,OSError):
                if(s in clients):
                    clients.remove(s)
                s.close()
                continue
        with runningMutex:
            # end of loop
            if(not running):break
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping")
except Exception as error: 
    print(
    type(error).__name__,          # TypeError
    __file__,                  # /tmp/example.py
    error.__traceback__.tb_lineno,  # 2
    error
    )
with runningMutex:
    while(running):running = False
backlogThread.join()
print("close all connections!")
for cl in clients:
    cl.close()
tcpServer.close()
udpServer.close()
backlogThread.join()
