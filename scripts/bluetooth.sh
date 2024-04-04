#!/bin/bash

# Définition du timeout pour la recherche, en secondes
SCAN_TIME=15

# Execute bluetoothctl show` et capture la sortie
output=$(bluetoothctl show)

# Utilise `grep` pour trouver la ligne contenant "Controller" et ensuite `awk` pour extraire l'adresse MAC
mac_address=$(echo "$output" | grep "Controller" | awk '{print $2}')

# Affiche l'adresse MAC
echo "L'adresse MAC du contrôleur Bluetooth est : $mac_address"

#Demande le nom du reseau bluetooth
read -p "Nom du bluetooth : " name



# Activation de l'agent et du contrôleur Bluetooth
echo -e 'power on\nagent on\ndefault-agent' | bluetoothctl



bluetoothctl system-alias $name


echo -e "\n\nLe nom Bluetooth a été changé en '$name'"




echo -e "\nNom de l'autre appareil à trouver :"
read other_device_name



echo -e "\nDébut du scan pendant $SCAN_TIME secondes"

(
    # Exécute bluetoothctl et redirige toute sortie vers /dev/null
    bluetoothctl discoverable on
    echo -e 'scan on'
    sleep $SCAN_TIME
    echo -e 'scan off\nexit'

    device_found=false

    i=0 # Initialisation du compteur de tentatives

    while [[ "$device_found" != true && $i -lt 5]]; do
        ((i++))
        # Capture la liste des appareils dans une variable
        devices_list=$(bluetoothctl devices)

        # Utilise grep pour chercher le nom spécifié dans la liste des appareils
        # puis utilise awk pour extraire l'adresse MAC du premier appareil correspondant
        mac_address=$(echo "$devices_list" | grep "$other_device_name" | awk '{print $2}' | head -n 1)

        if [[ -z "$mac_address" ]]; then
            sleep 2 # Attend 5 secondes avant de réessayer
        else
            device_found=true
        fi
    done


) | bluetoothctl > /dev/null 2>&1 &

wait


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


# Mise en confiance du périphérique
#echo -e "trust $mac_address" | bluetoothctl

# Appairage avec le périphérique
echo -e "pair $mac_address" | bluetoothctl

# Connexion au périphérique
echo -e "connect $mac_address" | bluetoothctl

# Affichage de l'état de la connexion
echo -e "info $mac_address" | bluetoothctl


echo -e "\n\n Connecter à l'adresse $mac_address"
echo "Fin du script"