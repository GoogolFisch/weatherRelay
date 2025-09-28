
import bluetooth
import util
import json
import select
import time

CONFIG_FILE = "./config.json"
with open(CONFIG_FILE,"r") as fptr:
    config_data = json.load(fptr)
serviceMap = {}
messageMap = {}
plugins = []
for k in config_data["services"]:
    data = __import__(k["file"])
    data.PORT = k["port"]
    data.MAIN = data.MAIN(k)
    plugins.append(data)
    serviceMap[data.PORT] = data

thisMac = util.Pair.srcMac
connections = []
blueServer = None
uuid = config_data["uuid"]
# setup server
if(config_data["server"]):
    blueServer = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    blueServer.bind(("",bluetooth.PORT_ANY))
    blueServer.listen(2)

    port = blueServer.getsockname()[1]
    bluetooth.advertise_service(blueServer, "BlueRelay", service_id=uuid,
                                service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
                                profiles=[bluetooth.SERIAL_PORT_PROFILE]
                                )
    connections.append(blueServer)
    print("started Server")

# setup client
if(config_data["client"]):
    services = bluetooth.find_service(uuid=uuid,address=None)
    print(services)
    for serv in services:
        port = serv["port"]
        name = serv["name"]
        host = serv["host"]
        print("Connecting to \"{}\" on {}".format(name, host))
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((host, port))
        connections.append(sock)

def readDataFromSocket(socket):
    data = ''
    buffer = ''
    try:
        while True:
            data = socket.recv(4096)
            if not data:break
            buffer += data
    except Exception as error: 
        print(
        type(error).__name__,          # TypeError
        __file__,                  # /tmp/example.py
        error.__traceback__.tb_lineno  # 2
        )
        print(f'socket.error - ({error})')
    if data: print('received', buffer)
    else:
        print('disconnected')
    return buffer

def main():
    try:
        message_queue = []
        counter = 0
        while True:
            counter += 1
            time.sleep(0.1)
            readable, writeable, exceptional = select.select(
                    connections,[],connections,1)
            for s in readable:
                if s is blueServer:
                    connection, client_address = blueServer.accept()
                    print(f"{connection=} {client_address=}")
                    connection.setblocking(0)
                    connections.append(connection)
                    continue
                else:
                    data = readDataFromSocket(s)
                    msg = Message.fromBytearray(data)
                    message_queue.append(msg)
                    print(data)
            for mes in message_queue:
                if(mes.dstPort != thisMac):
                    get = messageMap.get(mes.pair.uuid)
                    if(get is not None):
                        continue
                    messageMap[mes.pair.uuid] = mes
                    # relay messages!
                    for sc in connections:
                        sc.send(mes.getBytes())
                    continue
                pl = serviceMap[mes.dstPort]
                mesBin = pl.MAIN.readWrite(mes)
                for mes in mesBin:
                    for sc in connections:
                        sc.send(mes.getBytes())
            if(counter % 10 != 0):
                continue
            # no starve calling
            for pl in plugins:
                mesBin = pl.MAIN.readWrite(None)
                print(mesBin)
                for mes in mesBin:
                    for sc in connections:
                        sc.send(mes.getBytes())
    except KeyboardInterrupt:
        for c in connections:
            print(c)
            c.close()
        for pl in plugins:
            print(pl)
            pl.MAIN.close()
    print("Closed all")

if __name__ == '__main__':
    print("Main Loop")
    main()
