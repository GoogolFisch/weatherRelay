
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

def main():
    try:
        while True:
            time.sleep(0.1)
            readable, writeable, exceptional = select.select(
                    connections,[],connections,1)
            for s in readable:
                if s is blueServer:
                    connection, client_address = blueServer.accpet()
                    print(f"{connection=} {client_address=}")
                    connection.setblocking(0)
                    connections.append(connection)
                    continue
                else:
                    pass
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
