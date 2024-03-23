import argparse
from client import Client
from server import Server

def parse_arguments():
    parser = argparse.ArgumentParser(description="Client de transfert de fichiers.")
    parser.add_argument("--mode", type=str, required=True, choices=["server", "client"], help="Mode d'exécution")
    parser.add_argument("--host", type=str, required=True, help="Adresse du serveur")
    parser.add_argument("--port", type=int, required=True, help="Port du serveur")

    # client
    parser.add_argument("--download", type=str, help="Nom du fichier à télécharger")
    parser.add_argument("--upload", type=str, help="Chemin du fichier à uploader")
    parser.add_argument("--list", action="store_true", help="Lister les fichiers sur le serveur")

    return parser.parse_args()

def main():
    args = parse_arguments()

    if args.mode == "server":
        server = Server(args.host, args.port)
        server.start()
    else:
      client = Client(args.host, args.port)

      if args.upload:
          client.send_file(args.upload)

      client.close_connection()

if __name__ == "__main__":
    main()
