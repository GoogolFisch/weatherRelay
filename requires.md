
# Requirements

## Install
Ubuntu \
`apt install libbluretooth-dev` \
`pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez`
`pip install scapy`

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

## not having to accept every new device!
`sudo raspi-config`
and change under:
`System Options`
`S5 Boot`
to `B1 Console Text console`

## making these talk together!!

Specify an subnet that you don't want to use.
In my case `172.16.0.0/12`.
Then I made an custom arp lookup entry.
`sudo arp -s 172.17.0.1 00:0c:29:c0:84:bf`
NOTE: use an MAC-Address, that you don't have
and add an routing info with:
`ip route add 172.16.0.0/16 via 172.17.0.1`

This will trick your system into sending this data onto your private network,
but also allow you to have more time, to get an response from the bluetooth network.

## Optional
Adding this to crontab

`crontab -e` as root
and insert
`@reboot /home/pwd/start.sh`
