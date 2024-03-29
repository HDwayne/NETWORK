import hashlib
import threading
import socket
import os
import zlib
from message import Message
import random
import argparse


class ClientSession:
    def __init__(self, client_socket):
        self.socket = client_socket
        self.is_uploading = False
        self.file_data_buffer = bytearray()
        self.num_expected_acks = 0
        self.file_hash = None
        self.file_name = None
        self.file_compressed = None


class Server:
    def __init__(
        self,
        host,
        port,
        mac_address,
        files_directory,
        drop_test,
        drop_test_probability,
    ):
        self.host = host
        self.port = port
        self.mac_address = mac_address
        self.FILES_DIRECTORY = files_directory

        self.drop_test = drop_test
        self.drop_test_probability = drop_test_probability

    def start(self):
        server_blutooth_thread = threading.Thread(target=self._start_bluetooth)
        server_wifi_thread = threading.Thread(target=self._start_wifi)

        server_blutooth_thread.start()
        server_wifi_thread.start()

    def _start_wifi(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.bind((self.host, self.port))
                server_socket.listen()
                print(f"[Server WIFI] Server listening on {self.host}:{self.port}")

                while True:
                    client_socket, address = server_socket.accept()
                    print(f"[Server WIFI] Connection from {address}")
                    client_thread = threading.Thread(
                        target=self._handle_client, args=(ClientSession(client_socket),)
                    )
                    client_thread.start()
        except OSError as e:
            print(f"[Server WIFI] Wi-Fi error: {e}")
            exit(1)

    def _start_bluetooth(self):
        try:
            with socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
            ) as bluetooth_socket:
                bluetooth_socket.bind((self.mac_address, 1))
                bluetooth_socket.listen()
                print(f"[Server BLUETOOTH] Server listening on {self.mac_address}:1")

                while True:
                    client_socket, address = bluetooth_socket.accept()
                    print(f"[Server BLUETOOTH] Connection from {address}")
                    client_thread = threading.Thread(
                        target=self._handle_client, args=(ClientSession(client_socket),)
                    )
                    client_thread.start()
        except OSError as e:
            print(f"[Server BLUETOOTH] Bluetooth error: {e}")
            exit(1)

    def _handle_client(self, session):
        buffer = b""
        try:
            while True:
                data = session.socket.recv(2048)
                if not data:
                    break  # Connexion fermée par le client
                buffer += data

                while len(buffer) >= 4:
                    # Longueur du message attendu
                    message_length = int.from_bytes(buffer[:4], byteorder="big")
                    if len(buffer) - 4 >= message_length:
                        # Message complet reçu
                        message_data = buffer[4 : 4 + message_length]
                        buffer = buffer[4 + message_length :]

                        message = Message.deserialize(message_data)
                        self._process_message(message, session)
                    else:
                        break  # Attend plus de données
        except Exception as e:
            print(f"[Server Client] Error: {e}")
        finally:
            print("[Server Client] Client disconnected")
            session.socket.close()

    def _process_message(self, message, session):
        if message.type == "UPLOAD" and not session.is_uploading:
            self._handle_upload(session, message)
        elif message.type == "DATA" and session.is_uploading:
            self._handle_data(message, session)
        elif message.type == "EOF" and session.is_uploading:
            self._handle_eof(message, session)
        elif message.type == "EXECUTE":
            self._handle_execute(message, session)
        else:
            print(f"[Server Client] Invalid message type: {message.type}")

    # ---------------------------- FileTransmissionProtocol --------------------

    def _handle_upload(self, session, message):
        session.is_uploading = True
        session.file_data_buffer.clear()
        session.num_expected_acks = 0
        session.file_name = message.content["file_name"]
        session.file_hash = message.content["file_hash"]
        session.file_compressed = message.content["file_compressed"]

        print(f"[FileTransmissionProtocol] Receiving file: {session.file_name}")

    def _handle_data(self, message, session):
        if message.sequence_num != session.num_expected_acks:
            return

        if self.drop_test and random.random() < self.drop_test_probability:
            print(f"[FileTransmissionProtocol] Dropped packet {message.sequence_num}.")
            return

        if message.hash == hashlib.sha256(message.content).hexdigest():
            session.file_data_buffer.extend(message.content)
            session.num_expected_acks += 1
            Message("ACK", message.sequence_num).send(session.socket)
            print(f"[FileTransmissionProtocol] ACK {message.sequence_num}.")

    def _handle_eof(self, message, session):
        if session.file_compressed:
            print("[FileTransmissionProtocol] Decompressing file.")
            session.file_data_buffer = zlib.decompress(session.file_data_buffer)

        received_file_hash = hashlib.sha256(session.file_data_buffer).hexdigest()

        if received_file_hash == session.file_hash:
            if not os.path.exists(self.FILES_DIRECTORY):
                os.makedirs(self.FILES_DIRECTORY)
            file_path = os.path.join(self.FILES_DIRECTORY, session.file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
            with open(file_path, "wb") as file:
                file.write(session.file_data_buffer)
            print(
                "[FileTransmissionProtocol] EOF_ACK File transfer complete with hash verification."
            )
            Message("EOF_ACK", message.sequence_num).send(session.socket)
        else:
            print("[FileTransmissionProtocol] EOF_NACK Hash mismatch.")
            Message(
                "EOF_NACK", message.sequence_num, "EOF received. Hash mismatch."
            ).send(session.socket)

        session.is_uploading = False

    # ---------------------------- FileExecutionProtocol -----------------------

    def _handle_execute(self, message, session):
        Message("EXECUTE_ACK").send(session.socket)

        file_path = os.path.join(self.FILES_DIRECTORY, message.content["file_name"])
        if not os.path.exists(file_path):
            print(f"[FileExecutionProtocol] File not found: {file_path}")
            Message(
                "EXECUTE_ERROR",
                content=f"File not found: {message.content['file_name']}",
            ).send(session.socket)
            return

        print(f"[FileExecutionProtocol] Simulating execution of {file_path}")

        Message("EXECUTE_RESULT", content="File executed successfully.").send(
            session.socket
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client de transfert de fichiers.")

    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="Adresse du serveur",
    )
    parser.add_argument("--port", type=int, required=True, help="Port du serveur")
    parser.add_argument(
        "--mac-address", type=str, required=True, help="Adresse MAC du serveur"
    )

    # server arguments
    parser.add_argument(
        "--files-directory",
        type=str,
        default="files",
        help="Répertoire des fichiers",
    )
    parser.add_argument(
        "--drop-test",
        action="store_true",
        help="Activer le test de perte de paquets",
    )
    parser.add_argument(
        "--drop-test-probability",
        type=float,
        default=0.05,
        help="Probabilité de perte de paquets",
    )

    args = parser.parse_args()

    server = Server(
        args.host,
        args.port,
        args.mac_address,
        args.files_directory,
        args.drop_test,
        args.drop_test_probability,
    )
    server.start()
