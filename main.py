
import bluetooth
import rawsocketpy
import json
import select
import time


CONFIG_FILE = "./config.json"
with open(CONFIG_FILE,"r") as fptr:
    config_data = json.load(fptr)

# maybe add plugins?

# starting main part
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

# listening (socket)
rawSock = rawsocketpy.RawSocket("???",0xEEFA)

#rawSock.send()

blueServer.close()
for con in connections:
    con.close()
rawSock.close()
