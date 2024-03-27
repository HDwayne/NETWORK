import argparse
from client import Client
from server import Server


def parse_arguments():
    parser = argparse.ArgumentParser(description="Client de transfert de fichiers.")
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["server", "client"],
        help="Mode d'exécution",
    )
    parser.add_argument("--host", type=str, required=True, help="Adresse du serveur")
    parser.add_argument("--port", type=int, required=True, help="Port du serveur")
    parser.add_argument(
        "--mac-address", type=str, required=True, help="Adresse MAC du serveur"
    )

    # client arguments
    parser.add_argument(
        "--window-size",
        type=int,
        help="Taille de la fenêtre de transmission (client uniquement)",
    )
    parser.add_argument(
        "--segment-size",
        type=int,
        help="Taille des segments de données (client uniquement)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        help="Délai d'attente avant retransmission (client uniquement)",
    )

    # server arguments
    parser.add_argument(
        "--files-directory",
        type=str,
        help="Répertoire des fichiers (server uniquement)",
    )
    parser.add_argument(
        "--drop-test",
        action="store_true",
        help="Activer le test de perte de paquets (server uniquement)",
    )
    parser.add_argument(
        "--drop-test-probability",
        type=float,
        help="Probabilité de perte de paquets (server uniquement)",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.mode == "server":
        server = Server(
            args.host,
            args.port,
            args.mac_address,
            drop_test=args.drop_test,
            drop_test_probability=args.drop_test_probability,
        )
        server.start()
    else:
        client = Client(args.host, args.port, args.mac_address)
        while True:
            command = input("Enter a command: ")
            if command == "exit":
                break
            elif command == "list":
                client.request_list()
            elif command.startswith("upload"):
                file_path = command.split(" ")[1]
                client.send_file(file_path)
            elif command.startswith("execute"):
                file_name = command.split(" ")[1]
                mode = input("Enter the mode (WIFI or BLUETOOTH): ")
                client.execute_file(file_name, mode)


if __name__ == "__main__":
    main()
