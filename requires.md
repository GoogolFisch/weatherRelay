
# Requirements

## Install
Ubuntu \
`apt install libbluretooth-dev` \
`pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez`

## configs
`sudo hciconfig hci0 piscan`
### files
`/etc/systemd/system/dbus-org.bluez.service` \
Change: \
```
#ExecStart=/usr/libexec/bluetooth/bluetoothd --compat
ExecStart=/usr/libexec/bluetooth/bluetoothd --compat --noplugin=sap
ExecStartPost=/usr/bin/sdptool add SP
```
 \
 \
Create `/etc/systemd/system/var-run-sdp.path` \
Add: \
```
[Unit]
Descrption=Monitor /var/run/sdp

[Install]
WantedBy=bluetooth.service

[Path]
PathExists=/var/run/sdp
Unit=var-run-sdp.service
```

Create `/etc/systemd/system/var-run-sdp.service` \
Add: \
```
[Unit]
Description=Set permission of /var/run/sdp

[Install]
RequiredBy=var-run-sdp.path

[Service]
Type=simple
ExecStart=/bin/chgrp bluetooth /var/run/sdp
```
And run it with:

```
sudo systemctl daemon-reload
sudo systemctl enable var-run-sdp.path
sudo systemctl enable var-run-sdp.service
sudo systemctl start var-run-sdp.path
```
