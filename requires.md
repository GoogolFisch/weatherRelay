
# Requirements

## Install
Ubuntu \
`apt install libbluretooth-dev` \
`pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez`
`pip install scapy`

## not having to accept every new device!
`sudo raspi-config`
and change under:
`System Options`
`S5 Boot`
to `B1 Console Text console`

## Optional
Adding this to crontab

`crontab -e` as root
and insert
`@reboot /home/pwd/start.sh`

## making these talk together!!
**This is done automaticaly**
Specify an subnet that you don't want to use.
In my case `172.16.0.0/12`.
Then I made an custom arp lookup entry.
`sudo arp -s 172.17.0.1 00:0c:29:c0:84:bf`
NOTE: use an MAC-Address, that you don't have
and add an routing info with:
`ip route add 172.16.0.0/16 via 172.17.0.1`

This will trick your system into sending this data onto your private network,
but also allow you to have more time, to get an response from the bluetooth network.

