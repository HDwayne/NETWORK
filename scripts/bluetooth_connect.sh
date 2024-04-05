#!/bin/bash

# Définition du timeout pour la recherche, en secondes
SCAN_TIME=120

# Desactivation de l'agent et du contrôleur Bluetooth
echo -e 'power off\n' | bluetoothctl



# Activation de l'agent et du contrôleur Bluetooth
echo -e 'power on\nagent on\ndefault-agent' | bluetoothctl



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


echo -e "\nNom de l'autre appareil à trouver :"
read other_device_name



echo -e "\nDébut du scan pendant $SCAN_TIME secondes"

bluetoothctl scan on &
#echo -e 'scan on' | bluetoothctl

device_found=false

i=0 # Initialisation du compteur de tentatives


#Boucle while pour que tant que le device n'est pas trouvé, il continue de scanner 
while [[ "$device_found" != true && $i -lt $SCAN_TIME ]]; do
    ((i++)) 
    # Capture la liste des appareils dans une variable
    devices_list=$(bluetoothctl devices)

    # Utilise grep pour chercher le nom spécifié dans la liste des appareils
    # puis utilise awk pour extraire l'adresse MAC du premier appareil correspondant
    mac_address=$(echo "$devices_list" | grep "$other_device_name" | awk '{print $2}' | head -n 1)

    if [[ -z "$mac_address" ]]; then
        sleep 1 # Attend X secondes avant de réessayer
    else
        device_found=true
    fi
done

#bluetoothctl scan off &
echo -e 'scan off' | bluetoothctl



if [[ "$device_found" != true ]]; then
    # Si aucun appareil correspondant n'est trouvé, affiche tous les appareils
    echo "Aucun appareil trouvé correspondant à '$other_device_name'. Appareils Bluetooth à proximité détectés :"
    echo "$devices_list"

    read -p "Entrez l'adresse MAC de l'appareil auquel vous souhaitez vous connecter :" mac_address
else
    # Affiche l'adresse MAC de l'appareil correspondant
    echo -e "\nAppareil trouvé correspondant à '$other_device_name' avec l'adresse MAC : $mac_address"

    sleep 1
fi

echo "Connexion en cours à l'appareil avec l'adresse MAC : $mac_address"


#bluetoothctl pair $mac_address &

#sleep 5
bluetoothctl connect $mac_address


# Vérifie si l'appairage a réussi
#if echo "$pair_output" | grep -q "Pairing successful"; then
    # Connexion au périphérique
#    bluetoothctl connect $mac_address &

    # Affichage de l'état de la connexion
#    echo -e "info $mac_address" | bluetoothctl


#    echo -e "\n\n Mon adresse : $my_mac_address"
#    echo -e "\n Connecter à l'adresse $mac_address"
#else
#    echo "Impossible d'appairer la raspberry, tester une autre fois."
#fi



echo "Fin du script"

sleep 5

exec bash