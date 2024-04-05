#!/bin/bash



# Liste tous les appareils connus et extrait leurs adresses MAC
devices=$(bluetoothctl devices | awk '{print $2}')

# Boucle sur chaque adresse MAC et supprime l'appareil
for mac in $devices; do
    echo "Suppression de l'appareil : $mac"
    echo -e "remove $mac" | bluetoothctl
done

echo "Tous les appareils connus ont été supprimés."


# Execute bluetoothctl show` et capture la sortie
output=$(bluetoothctl show)

# Utilise `grep` pour trouver la ligne contenant "Controller" et ensuite `awk` pour extraire l'adresse MAC
my_mac_address=$(echo "$output" | grep "Controller" | awk '{print $2}')

# Affiche l'adresse MAC
echo "L'adresse MAC du contrôleur Bluetooth est : $my_mac_address"

#Demande le nom du reseau bluetooth
read -p "Nom du bluetooth : " name



# Activation de l'agent et du contrôleur Bluetooth
echo -e 'power on\nagent on\ndefault-agent' | bluetoothctl



bluetoothctl system-alias $name


echo -e "\n\nLe nom Bluetooth a été changé en '$name'"

bluetoothctl discoverable on

bluetoothctl pairable on


echo "Bluetooth appairable"
echo "Fin du script"