import socket
import os
import hashlib
import threading
import time
from message import Message
import argparse
import zlib


class Client:
    class FileTransmissionProtocol:
        def __init__(
            self,
            client,
            window_size,
            segment_size,
            timeout,
            compression,
            connection_mode,
        ):
            self.client = client
            self._window_size = window_size
            self._segment_size = segment_size
            self._timeout = timeout
            self._compression = compression

            self._socket = None
            self._current_base = None
            self._segments_to_send = None
            self._retransmission_in_progress = False
            self._transmission_lock = threading.Lock()
            self._transmission_status = "NOT_STARTED"
            self._connection_mode = connection_mode  # BLUETOOTH or WIFI

        def _connect(self):
            try:
                if self._connection_mode == "BLUETOOTH":
                    self._socket = socket.socket(
                        socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
                    )
                else:
                    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                for attempt in range(5):
                    try:
                        if self._connection_mode == "BLUETOOTH":
                            self._socket.connect((self.client.mac_address, 1))
                        else:
                            self._socket.connect(
                                (self.client.server_address, self.client.server_port)
                            )
                        print(
                            "[FileTransmissionProtocol] Connecté avec succès au serveur pour l'exécution de commandes."
                        )
                        return True
                    except socket.error as e:
                        print(
                            f"[FileTransmissionProtocol] Échec de la connexion au serveur, tentative {attempt + 1}/5"
                        )
                        if attempt < 4:
                            time.sleep(2)
                        else:
                            print(
                                "[FileTransmissionProtocol] Impossible de se connecter au serveur pour l'exécution de commandes."
                            )
                            return False
            except Exception as e:
                print(f"Error connecting to server: {e}")
                return False

        def _disconnect(self):
            if self._socket:
                self._socket.close()
                print(
                    "[FileTransmissionProtocol] Déconnecté du serveur de transfert de fichier."
                )

        def _reconnect(self):
            while True:
                try:
                    if self._connection_mode == "BLUETOOTH":
                        self._socket = socket.socket(
                            socket.AF_BLUETOOTH,
                            socket.SOCK_STREAM,
                            socket.BTPROTO_RFCOMM,
                        )
                    else:
                        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                except Exception as e:
                    print(f"Error reconnecting to server: {e}")
                    continue

        def send_file(self, file_path):
            if not self._connect():
                return
            self._transmission_status = "IN_PROGRESS"
            threading.Thread(target=self._listen_server, daemon=True).start()

            with open(file_path, "rb") as file:
                if self._compression:
                    segments = zlib.compress(file.read())
                else:
                    segments = file.read()

            self._segments_to_send = [
                segments[i : i + self._segment_size]
                for i in range(0, len(segments), self._segment_size)
            ]

            self._send_upload(file_path)

            self._current_base = 0
            seq_num = 0
            while seq_num < len(self._segments_to_send):
                with self._transmission_lock:
                    if (
                        not self._retransmission_in_progress
                        and seq_num <= self._current_base + self._window_size - 1
                    ):
                        self._send_data(self._segments_to_send[seq_num], seq_num)
                        seq_num += 1

            # Attendre que tous les ACKs soient reçus avant de conclure
            while self._current_base < len(self._segments_to_send):
                time.sleep(0.1)

            self._send_eof()

            # Attendre que le serveur réponde avec un EOF_ACK ou EOF_NACK
            while self._transmission_status == "IN_PROGRESS":
                time.sleep(0.1)

            self._segments_to_send = None
            print(f"Transmission status: {self._transmission_status}")
            self._disconnect()

        def _send_upload(self, file_path):
            file_name = os.path.basename(file_path)
            file_hash = self._calculate_file_hash(file_path)
            try:
                Message(
                    "UPLOAD",
                    content={
                        "file_name": file_name,
                        "file_hash": file_hash,
                        "file_compressed": self._compression,
                    },
                ).send(self._socket)
            except socket.error:
                self._reconnect()
            print(f"[FileTransmissionProtocol] Sent upload message for {file_name}")

        def _send_data(self, data, sequence_num):
            data_hash = hashlib.sha256(data).hexdigest()
            try:
                Message("DATA", sequence_num, data, data_hash).send(self._socket)
            except socket.error:
                self._reconnect()
            setattr(
                self,
                f"_timer_{sequence_num}",
                threading.Timer(
                    self._timeout, self._check_timeout, args=(sequence_num,)
                ),
            )
            getattr(self, f"_timer_{sequence_num}").start()
            print(f"[FileTransmissionProtocol] Sent data segment {sequence_num}")

        def _send_eof(self):
            try:
                Message("EOF").send(self._socket)
            except socket.error:
                self._reconnect()
            print(f"[FileTransmissionProtocol] Sent EOF segment")

        def _calculate_file_hash(self, file_path):
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()

        def _check_timeout(self, seq_num):
            with self._transmission_lock:
                if (
                    seq_num > self._current_base
                    and not self._retransmission_in_progress
                ):
                    self._retransmission_in_progress = True

                    print(
                        f"[Timeout] detected for segment {seq_num}, initiating retransmission from base {self._current_base}."
                    )
                    end_window = min(
                        self._current_base + self._window_size,
                        len(self._segments_to_send),
                    )
                    for seq_num in range(self._current_base, end_window):
                        print(f"[Timeout] Retransmitting segment {seq_num}")
                        self._send_data(self._segments_to_send[seq_num], seq_num)

                    self._retransmission_in_progress = False

        def _listen_server(self):
            buffer = b""
            while True:
                try:
                    data = self._socket.recv(2048)
                    if not data:
                        break  # La connexion a été fermée
                    buffer += data

                    # Continuez à essayer de traiter les messages tant que vous avez assez de données dans le buffer
                    while (
                        len(buffer) >= 4
                    ):  # Vérifiez si vous avez la longueur du message
                        message_length = int.from_bytes(buffer[:4], byteorder="big")

                        # Assurez-vous d'avoir reçu le message complet
                        if len(buffer) - 4 >= message_length:
                            message_data = buffer[4 : 4 + message_length]
                            buffer = buffer[
                                4 + message_length :
                            ]  # Supprimez les données traitées du buffer

                            ack_message = Message.deserialize(message_data)
                            if ack_message.type == "ACK":
                                print(
                                    f"[Server] ACK for segment {ack_message.sequence_num}"
                                )
                                if hasattr(self, f"_timer_{ack_message.sequence_num}"):
                                    getattr(
                                        self, f"_timer_{ack_message.sequence_num}"
                                    ).cancel()
                                    delattr(self, f"_timer_{ack_message.sequence_num}")
                                self._current_base = max(
                                    self._current_base, ack_message.sequence_num + 1
                                )
                            elif ack_message.type == "EOF_ACK":
                                print("[Server] EOF ACK")
                                self._transmission_status = "SUCCESS"
                            elif ack_message.type == "EOF_NACK":
                                print(f"[Server] EOF NACK : {ack_message.content}")
                                self._transmission_status = "FAILED"
                        else:
                            break
                except Exception as e:
                    print(f"Error listening for messages: {e}")
                    break

    class FileExecutionProtocol:
        def __init__(self, client, connection_mode):
            self.client = client
            self._sock = None
            self._connection_mode = connection_mode  # BLUETOOTH or WIFI

        def _connect(self):
            try:
                if self._connection_mode == "BLUETOOTH":
                    self._sock = socket.socket(
                        socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
                    )
                else:
                    self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                for attempt in range(5):
                    try:
                        if self._connection_mode == "BLUETOOTH":
                            self._sock.connect((self.client.mac_address, 1))
                        else:
                            self._sock.connect(
                                (self.client.server_address, self.client.server_port)
                            )
                        print(
                            "[FileExecutionProtocol] Connecté avec succès au serveur pour l'exécution de commandes."
                        )
                        return True
                    except socket.error as e:
                        print(
                            f"[FileExecutionProtocol] Échec de la connexion au serveur, tentative {attempt + 1}/5"
                        )
                        if attempt < 4:
                            time.sleep(2)
                        else:
                            print(
                                "[FileExecutionProtocol] Impossible de se connecter au serveur pour l'exécution de commandes."
                            )
                            return False
            except Exception as e:
                print(f"Error connecting to server: {e}")
                return False

        def _disconnect(self):
            if self._sock:
                self._sock.close()
                print(
                    "[FileExecutionProtocol] Déconnecté du serveur pour l'exécution de commandes."
                )

        def execute_file(self, file_name):
            if not self._connect():
                return

            try:
                Message("EXECUTE", content={"file_name": file_name}).send(self._sock)
            except socket.error:
                self._disconnect()
            print(f"[FileExecutionProtocol] Sent execute message for {file_name}")

            buffer = b""
            while True:
                try:
                    data = self._sock.recv(2048)
                    if not data:
                        break  # La connexion a été fermée
                    buffer += data

                    # Continuez à essayer de traiter les messages tant que vous avez assez de données dans le buffer
                    while (
                        len(buffer) >= 4
                    ):  # Vérifiez si vous avez la longueur du message
                        message_length = int.from_bytes(buffer[:4], byteorder="big")

                        # Assurez-vous d'avoir reçu le message complet
                        if len(buffer) - 4 >= message_length:
                            message_data = buffer[4 : 4 + message_length]
                            buffer = buffer[
                                4 + message_length :
                            ]  # Supprimez les données traitées du buffer

                            message = Message.deserialize(message_data)
                            if message.type == "EXECUTE_ACK":
                                print(
                                    "[FileExecutionProtocol] Request to execute file acknowledged."
                                )
                            elif message.type == "EXECUTE_ERROR":
                                print(
                                    f"[FileExecutionProtocol] EXECUTE NACK : {message.content}"
                                )
                                self._disconnect()
                                return
                            elif message.type == "EXECUTE_RESULT":
                                print(
                                    f"[FileExecutionProtocol] EXECUTE RESULT : {message.content}"
                                )
                                self._disconnect()
                                return
                            else:
                                print(
                                    f"[FileExecutionProtocol] Invalid message type: {message.type}"
                                )
                                self._disconnect()
                                return
                        else:
                            break
                except Exception as e:
                    print(f"Error listening for messages: {e}")
                    break

    def __init__(self, server_address, server_port, mac_address):
        self.server_address = server_address
        self.server_port = server_port
        self.mac_address = mac_address

    def send_file(
        self,
        file_path,
        window_size,
        segment_size,
        timeout,
        compression,
        connection_mode,
    ):
        self.FileTransmissionProtocol(
            self, window_size, segment_size, timeout, compression, connection_mode
        ).send_file(file_path)

    def execute_file(self, file_name, connection_mode):
        self.FileExecutionProtocol(self, connection_mode=connection_mode).execute_file(
            file_name
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client for file transfer")

    # required arguments
    parser.add_argument(
        "--host",
        type=str,
        required=True,
        help="Adresse IP du serveur",
    )
    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Port du serveur",
    )
    parser.add_argument(
        "--mac-address",
        type=str,
        required=True,
        help="Adresse MAC du serveur (pour la connexion Bluetooth)",
    )

    # optional arguments
    parser.add_argument(
        "--window-size",
        type=int,
        default=10,
        help="Taille de la fenêtre de transmission",
    )
    parser.add_argument(
        "--segment-size",
        type=int,
        default=2048,
        help="Taille des segments de données",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Délai d'attente avant retransmission",
    )
    parser.add_argument(
        "--compression",
        type=bool,
        default=True,
        help="Activer la compression des données",
    )

    args = parser.parse_args()
    client = Client(args.host, args.port, args.mac_address)

    while True:
        command = input("Enter command: ")
        if command == "exit":
            break
        elif command.startswith("upload"):
            if len(command.split(" ")) != 2:
                print("upload command requires a file path.")
                continue
            _, file_path = command.split(" ")
            if not os.path.exists(file_path):
                print(f"File {file_path} does not exist.")
                continue
            connection_mode = input("Enter connection mode (BLUETOOTH or WIFI): ")
            if connection_mode not in ["BLUETOOTH", "WIFI"]:
                print("Invalid connection mode")
                continue
            client.send_file(
                file_path,
                args.window_size,
                args.segment_size,
                args.timeout,
                args.compression,
                connection_mode,
            )
        elif command.startswith("execute"):
            if len(command.split(" ")) != 2:
                print("execute command requires a file name.")
                continue
            _, file_name = command.split(" ")
            connection_mode = input("Enter connection mode (BLUETOOTH or WIFI): ")
            if connection_mode not in ["BLUETOOTH", "WIFI"]:
                print("Invalid connection mode")
                continue
            client.execute_file(file_name, connection_mode)
        else:
            print("Invalid command")
