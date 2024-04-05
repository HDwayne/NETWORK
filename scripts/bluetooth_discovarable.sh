#!/bin/bash


# Lance bluetoothctl, puis utilise des commandes pour lister et supprimer les appareils
bluetoothctl << EOF
devices | grep Device | cut -d ' ' -f 2 | while read mac; do remove $mac; done
exit
EOF

echo "Tous les appareils appairés ont été supprimés."


# Execute bluetoothctl show` et capture la sortie
output=$(bluetoothctl show)

# Utilise `grep` pour trouver la ligne contenant "Controller" et ensuite `awk` pour extraire l'adresse MAC
my_mac_address=$(echo "$output" | grep "Controller" | awk '{print $2}')

# Affiche l'adresse MAC
echo "L'adresse MAC du contrôleur Bluetooth est : $mac_address"

#Demande le nom du reseau bluetooth
read -p "Nom du bluetooth : " name



# Activation de l'agent et du contrôleur Bluetooth
echo -e 'power on\nagent on\ndefault-agent' | bluetoothctl



bluetoothctl system-alias $name


echo -e "\n\nLe nom Bluetooth a été changé en '$name'"

bluetoothctl discovarable on

bluetoothctl pairable on


echo "Bluetooth appairable"
echo "Fin du script"