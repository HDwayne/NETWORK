
#!/bin/bash

#Se script permet la mise en place d'un réseau adhoc en bare metal sur une raspbery.


read -p "Interface reseau : " interface
read -p "SSID name : " ssid
read -p "Cannal a utilise : " cannal
read -p "IP : " ip

sudo killall wpa_supplicant

sudo ifconfig $interface down

sudo iwconfig $interface mode ad-hoc

sudo iwconfig $interface channel 4

sudo iwconfig $interface essid $ssid

sudo iwconfig $interface key off

sudo ifconfig $interface $ip netmask 255.255.255.0

sudo ifconfig $interface up

echo "Mode ad-hoc activé sur $ip"
