#!/bin/bash

# Execute bluetoothctl show` et capture la sortie
output=$(bluetoothctl show)

# Utilise `grep` pour trouver la ligne contenant "Controller" et ensuite `awk` pour extraire l'adresse MAC
mac_address=$(echo "$output" | grep "Controller" | awk '{print $2}')

# Affiche l'adresse MAC
echo "L'adresse MAC du contrôleur Bluetooth est : $mac_address"


bluetoothctl discoverable on
echo -e "\nAttente de 3 secondes"
sleep 3


# Se connecter à un autre appareil avec bluetoothctl
echo -e "\nRecherche d'appareils Bluetooth disponibles..."
devices=$(bluetoothctl devices)
echo "$devices"

echo -e "\nEntrez l'adresse MAC de l'appareil auquel vous souhaitez vous connecter :"
read mac_address

echo "Connexion en cours à l'appareil avec l'adresse MAC : $mac_address"

# Connexion à l'appareil via bluetoothctl
bluetoothctl connect $mac_address

echo "Connexion établie."


bluetoothctl discoverable off
