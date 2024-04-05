# Application de Transfert de Fichiers

## Description

Cette application permet le transfert de fichiers entre un client et un serveur. Elle supporte la compression des données, assure l'intégrité des fichiers à travers des vérifications de hachage, et permet l'exécution d'un fichiers transférés.

## Fonctionnement

L'application se compose de trois modules principaux :
- **Serveur (`server.py`)** : Écoute sur des ports spécifiés pour les connexions supportant la famille d'adresses AF_INET ainsi que les connexions Bluetooth. Gère les fichiers reçus et exécute des commandes sur ces fichiers.
- **Client (`client.py`)** : Envoie des fichiers et des commandes d'exécution au serveur.
- **Messages (`message.py`)** : Définit le format des messages pour la communication entre le client et le serveur.

## Usages

Pour utiliser l'application, vous devez démarrer le serveur et le client avec les configurations appropriées.

### Démarrage du Serveur

Lancez le serveur en spécifiant les arguments nécessaires. Voici un tableau des arguments disponibles :

| Argument         | Description                                         | Valeur par Défaut      | Requis   |
|------------------|-----------------------------------------------------|------------------------|----------|
| `--host`         | Adresse IP sur laquelle le serveur doit écouter     | Aucune                 | Oui      |
| `--port`         | Port sur lequel le serveur doit écouter             | Aucune                 | Oui      |
| `--mac-address`  | Adresse MAC du serveur (pour connexion Bluetooth)   | Aucune                 | Oui      |
| `--files-directory` | Répertoire où les fichiers seront stockés         | `./files`              | Non      |
| `--drop-test`    | Active le test de simulation de perte de paquets    | Désactivé (`False`)    | Non      |
| `--drop-test-probability` | Probabilité de perte de paquet pour le test | `0.05`                 | Non      |

Commande exemple pour démarrer le serveur :
```shell
python server.py --host 127.0.0.1 --port 12345 --mac-address AA:BB:CC:DD:EE:FF
```

### Utilisation du Client

Connectez le client au serveur en spécifiant les arguments nécessaires. Voici un tableau des arguments disponibles pour le client :

| Argument         | Description                                           | Valeur par Défaut    | Requis   |
|------------------|-------------------------------------------------------|----------------------|----------|
| `--host`         | Adresse IP du serveur                                 | Aucune               | Oui      |
| `--port`         | Port du serveur                                       | Aucune               | Oui      |
| `--mac-address`  | Adresse MAC du serveur (pour connexion Bluetooth)     | Aucune               | Oui      |
| `--window-size`  | Taille de la fenêtre de transmission pour le protocole Go-Back-N | `10`  | Non      |
| `--segment-size` | Taille des segments de données en octets              | `2048`               | Non      |
| `--timeout`      | Délai d'attente avant retransmission en secondes      | `2.0`                | Non      |
| `--compression`  | Active la compression des données avant l'envoi       | Activé (`True`)      | Non      |

Commande exemple pour connecter le client et envoyer un fichier :
```shell
python client.py --host 127.0.0.1 --port 12345 --mac-address AA:BB:CC:DD:EE:FF
```
Ensuite, suivez les instructions à l'écran pour envoyer des fichiers ou exécuter des commandes.

- Pour envoyer un fichier, tapez : `upload <chemin_vers_fichier>`.
- Pour exécuter un fichier sur le serveur, tapez : `execute <nom_fichier>`, Puis renseignez le mode de connexion (`WIFI` ou `BLUETOOTH`).


## Protocoles

## Protocole de Transfert de Fichier (FileTransmissionProtocol)

Ce protocole, inspiré par le protocole Go-Back-N, gère le transfert de fichiers du client vers le serveur.
mode de transfert possible : Wi-Fi ou Bluetooth.

### Déroulement

1. **Initialisation du Transfert** : Le client commence par envoyer un message de type **UPLOAD** pour signaler le début du transfert d'un fichier. Le nom du fichier, son hachage sont inclus dans ce message. Le client précise également au server si le fichier est compressé ou non.
   
2. **Envoi Séquentiel avec Fenêtre d'Envoi** : Le fichier est divisé en segments. Le client envoie plusieurs segments, sans attendre un accusé de réception (**ACK**) pour chaque segment, jusqu'à atteindre la limite de la fenêtre d'envoi.
   
3. **Accusés de Réception et Retransmission** : 
    - Le serveur envoie un message **ACK** après la réception de chaque segment attendu, indiquant le dernier segment reçu avec succès.
    - Si le client ne reçoit pas d'**ACK** pour un segment avant l'expiration du délai (timeout), il retransmet tous les segments de la fenêtre, conformément au comportement Go-Back-N.
   
4. **Fin de Transfert** : Une fois tous les segments du fichier envoyés, le client envoie un message de type **EOF** (End of File) pour indiquer la fin du transfert.
   
5. **Confirmation de Réception Complète** :
    - Le serveur répond avec un **EOF_ACK** pour confirmer la réception complète et l'intégrité du fichier.
    - Si le serveur détecte qu'il manque des segments ou que la vérification de l'intégrité du fichier échoue, il envoye un **EOF_NACK** avec un commentaire sur l'erreur rencontrée.

### Types de Messages

- **UPLOAD** : Indique le début du transfert d'un fichier.
- **DATA** : Contient un segment du fichier à transférer.
- **ACK** : Accusé de réception envoyé par le serveur pour confirmer la réception d'un ou plusieurs segments.
- **EOF** : Marque la fin du transfert du fichier.
- **EOF_ACK** : Confirmation par le serveur de la réception complète et de l'intégrité du fichier.
- **EOF_NACK** : Indique une erreur dans la réception du fichier, demandant une retransmission.

## Protocole d'Exécution de Fichier (FileExecutionProtocol)

Ce protocole permet au client de demander l'exécution d'un fichier spécifique sur le serveur, en utilisant soit une connexion Wi-Fi soit Bluetooth.

### Déroulement

1. **Demande d'Exécution** : le client envoie un message **EXECUTE** au serveur, spécifiant le nom du fichier à exécuter ainsi que le mode de connexion souhaité (Wi-Fi ou Bluetooth).

2. **Accusé de Réception** : Le serveur répond avec un **EXECUTE_ACK** pour confirmer la réception de la commande d'exécution. Cette réponse assure au client que le serveur a bien reçu la demande et qu'il est en train de préparer l'exécution du fichier demandé.

3. **Exécution et Résultat** : 
    - Le serveur tente d'exécuter le fichier spécifié. Selon le résultat de cette exécution, le serveur peut envoyer différents types de messages au client :
        - **EXECUTE_RESULT** : Envoyé si le fichier a été exécuté avec succès. Ce message inclut le résultat de l'exécution, permettant au client de recevoir des informations sur l'opération effectuée.
        - **EXECUTE_ERROR** : Envoyé si une erreur survient pendant la tentative d'exécution du fichier (par exemple, si le fichier n'existe pas ou s'il y a eu une erreur d'exécution). Ce message fournit des détails sur l'erreur rencontrée.

### Types de Messages

- **EXECUTE** : Commande envoyée par le client pour demander l'exécution d'un fichier.
- **EXECUTE_ACK** : Accusé de réception envoyé par le serveur, confirmant la prise en charge de la demande d'exécution.
- **EXECUTE_ERROR** : Message d'erreur envoyé par le serveur si l'exécution ne peut pas être réalisée, avec des détails sur l'erreur.
- **EXECUTE_RESULT** : Résultat de l'exécution envoyé par le serveur au client, incluant les données de sortie de l'exécution ou la confirmation de succès.
