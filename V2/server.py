import hashlib
import threading
import socket
import os
import time
from message import Message
import random
class ClientSession:
    def __init__(self):
        self.is_uploading = False
        self.file_name = None
        self.expected_hash = None
        self.file_data_buffer = bytearray()
        self.num_expected_acks = 0

class Server:

    def __init__(self, host, port, files_directory="./files", drop_test=False, drop_test_probability=0.05):
        self.host = host
        self.port = port
        self.FILES_DIRECTORY = files_directory

        self.drop_test = drop_test
        self.drop_test_probability = drop_test_probability

        if not os.path.exists(self.FILES_DIRECTORY):
            os.makedirs(self.FILES_DIRECTORY)
    
    # ---------------------------- PUBLIC METHODS ------------------------------

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"[Server] Server listening on {self.host}:{self.port}")
            
            while True:
                client_socket, address = server_socket.accept()
                print(f"[Server-Client] Connection from {address}")
                client_thread = threading.Thread(target=self._handle_client, args=(client_socket,))
                client_thread.start()
    
    # ---------------------------- PRIVATE METHODS -----------------------------

    def _handle_client(self, client_socket):
        session_state = ClientSession()

        try:
            while True:
                message_length_bytes = client_socket.recv(4)
                if message_length_bytes:
                    data_length = int.from_bytes(message_length_bytes, byteorder='big')
                    data = client_socket.recv(data_length)
                    message = Message.deserialize(data)
                    self._process_message(client_socket, message, session_state)
        except Exception as e:
            print(f"[Server-Client] Error : {e}")
        finally:
            print("[Server-Client] Client disconnected")
            client_socket.close()
    
    def _process_message(self, client_socket, message, session_state):
        if message.type == "UPLOAD" and not session_state.is_uploading:
            self._handle_upload(session_state, message)
        elif message.type == "DATA" and session_state.is_uploading:
            self._handle_data(client_socket, message, session_state)
        elif message.type == "EOF" and session_state.is_uploading:
            self._handle_eof(client_socket, message, session_state)
        else:
            print(f"[Server-Client] Invalid message type: {message.type}")

    def _handle_upload(self, session_state, message):
        session_state.is_uploading = True
        session_state.file_name = message.content["file_name"]
        session_state.expected_hash = message.content["file_hash"]
        session_state.file_data_buffer.clear()
        session_state.num_expected_acks = 0
        print(f"[Server-Client] Receiving file: {session_state.file_name}")
    
    def _handle_data(self, client_socket, message, session_state):
        if message.sequence_num != session_state.num_expected_acks:
            return

        received_data = message.content
        calculated_hash = hashlib.sha256(received_data).hexdigest()

        # randomly drop packets to simulate packet loss
        if self.drop_test and random.random() < self.drop_test_probability:
            print(f"[Server-Client] Dropped packet {message.sequence_num}.")
            return
        
        if calculated_hash != message.hash:
            nack_message = Message("NACK", message.sequence_num, "Hash mismatch")
            self._send_message(client_socket, nack_message)
            print(f"[Server-Client] NACK {message.sequence_num} : Mismatch in data hash.")
        else:
            session_state.file_data_buffer.extend(received_data)
            session_state.num_expected_acks += 1
            ack_message = Message("ACK", message.sequence_num)
            self._send_message(client_socket, ack_message)
            print(f"[Server-Client] ACK {message.sequence_num}.")

    def _handle_eof(self, client_socket, message, session_state):
        received_file_hash = hashlib.sha256(session_state.file_data_buffer).hexdigest()
        
        if received_file_hash == session_state.expected_hash:
            file_path = os.path.join(self.FILES_DIRECTORY, session_state.file_name)
            with open(file_path, "wb") as file:
                file.write(session_state.file_data_buffer)
            print("[Server-Client] EOF_ACK File transfer complete with hash verification.")
            ack_message = Message("EOF_ACK", message.sequence_num)
        else:
            print("[Server-Client] EOF_NACK Hash mismatch.")
            ack_message = Message("EOF_NACK", message.sequence_num, "EOF received. Hash mismatch.")
        
        self._send_message(client_socket, ack_message)
        session_state.is_uploading = False

    def _send_message(self, socket, message):
        serialized_message = message.serialize()
        message_length = len(serialized_message).to_bytes(4, byteorder='big')
        socket.send(message_length + serialized_message)