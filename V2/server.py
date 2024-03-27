import hashlib
import threading
import socket
import os
from message import Message
import random


class ClientSession:
    def __init__(self, client_socket):
        self.socket = client_socket
        self.is_uploading = False
        self.file_name = None
        self.expected_hash = None
        self.file_data_buffer = bytearray()
        self.num_expected_acks = 0


class Server:

    def __init__(
        self,
        host,
        port,
        files_directory="./files",
        drop_test=False,
        drop_test_probability=0.05,
    ):
        self.host = host
        self.port = port
        self.FILES_DIRECTORY = files_directory

        self.drop_test = drop_test
        self.drop_test_probability = drop_test_probability

    # ---------------------------- PUBLIC METHODS ------------------------------

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"[Server] Server listening on {self.host}:{self.port}")

            while True:
                client_socket, address = server_socket.accept()
                print(f"[Server-Client] Connection from {address}")
                client_thread = threading.Thread(
                    target=self._handle_client, args=(ClientSession(client_socket),)
                )
                client_thread.start()

    # ---------------------------- PRIVATE METHODS -----------------------------

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
            print(f"[Server-Client] Error: {e}")
        finally:
            print("[Server-Client] Client disconnected")
            session.socket.close()

    def _process_message(self, message, session):
        if message.type == "UPLOAD" and not session.is_uploading:
            self._handle_upload(session, message)
        elif message.type == "DATA" and session.is_uploading:
            self._handle_data(message, session)
        elif message.type == "EOF" and session.is_uploading:
            self._handle_eof(message, session)
        # elif message.type == "LIST":
        #     self._handle_list(session)
        # elif message.type == "EXECUTE":
        #     self._handle_execute(message, session)
        else:
            print(f"[Server-Client] Invalid message type: {message.type}")

    # ---------------------------- FileTransmissionProtocol --------------------

    def _handle_upload(self, session, message):
        session.is_uploading = True
        session.file_name = message.content["file_name"]
        session.expected_hash = message.content["file_hash"]
        session.file_data_buffer.clear()
        session.num_expected_acks = 0

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
        received_file_hash = hashlib.sha256(session.file_data_buffer).hexdigest()

        if received_file_hash == session.expected_hash:
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

    # ---------------------------- FileListRequestProtocol ---------------------

    # def _handle_list(self, client_socket):
    #     if not os.path.exists(self.FILES_DIRECTORY):
    #         os.makedirs(self.FILES_DIRECTORY)
    #     files = os.listdir(self.FILES_DIRECTORY)
    #     files_message = Message("LIST_RESPONSE", 0, files)
    #     self._send_message(client_socket, files_message)
    #     print("[Server-Client] Sending list of files.")

    # ---------------------------- FileExecutionProtocol -----------------------

    # def _handle_execute(self, client_socket, message):
    #     file_name = message.content["file_name"]
    #     file_path = os.path.join(self.FILES_DIRECTORY, file_name)
    #     if os.path.exists(file_path):
    #         execute_message = Message("EXECUTE_OK", 0, file_name)
    #     else:
    #         execute_message = Message("EXECUTE_KO", 0, "File not found.")
    #     self._send_message(client_socket, execute_message)
    #     print(f"[Server-Client] Sending file {file_name} to client.")
