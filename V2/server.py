import hashlib
import threading
import socket
import os
from message import Message

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.FILES_DIRECTORY = "./files"
        if not os.path.exists(self.FILES_DIRECTORY):
            os.makedirs(self.FILES_DIRECTORY)
    
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"Server listening on {self.host}:{self.port}")
            
            while True:
                client_socket, address = server_socket.accept()
                print(f"Connection from {address}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.start()
    
    # based on Go-Back-N protocol
    def handle_client(self, client_socket):
        session_state = {"is_uploading": False, "file_name": None, "file_data_buffer": bytearray(), "data_received_size": 1024, "num_acks": 0}
        try:
            while True:
                data = client_socket.recv(session_state["data_received_size"])
                if not data:
                    break
                
                message = Message.deserialize(data)
                self.process_message(client_socket, message, session_state)
        except Exception as e:
            print(f"Error in handle_client: {e}")
        finally:
            print("Client disconnected")
            client_socket.close()
    
    def process_message(self, client_socket, message, session_state):
        if message.type == "UPLOAD":
            self.start_upload(session_state, message)
        elif message.type == "DATA" and session_state["is_uploading"]:
            self.handle_data(client_socket, message, session_state)
        elif message.type == "EOF" and session_state["is_uploading"]:
            self.finish_upload(client_socket, message, session_state)
        elif message.type == "HANDSHAKE":
            self.handle_handshake(client_socket, message, session_state)

    def start_upload(self, session_state, message):
        session_state["is_uploading"] = True
        session_state["file_name"] = message.content["file_name"]
        session_state["expected_hash"] = message.content["file_hash"]
        session_state["file_data_buffer"].clear()
        print(f"Receiving file: {message.content['file_name']}")
    
    
    def handle_data(self, client_socket, message, session_state):
        received_data = message.content
        calculated_hash = hashlib.sha256(received_data).hexdigest()
        
        # Vérification si le hash calculé correspond au hash reçu
        if calculated_hash != message.hash:
            nack_message = Message("NACK", message.sequence_num, "Hash mismatch")
            # client_socket.send(nack_message.serialize())
            self.send_message(client_socket, nack_message)
            print(f"[NACK] Mismatch in data hash for sequence number: {message.sequence_num}. {len(nack_message.serialize())}")
        else:
            if message.sequence_num == session_state["num_acks"]:
                
                session_state["file_data_buffer"].extend(received_data)
                session_state["num_acks"] = session_state["num_acks"] + 1 % 10
                ack_message = Message("ACK", message.sequence_num)
                # client_socket.send(ack_message.serialize())
                self.send_message(client_socket, ack_message)
                print(f"[ACK] for data segment {message.sequence_num}. {len(ack_message.serialize())}")


    def finish_upload(self, client_socket, message, session_state):
        file_path = os.path.join(self.FILES_DIRECTORY, session_state["file_name"])
        received_file_hash = hashlib.sha256(session_state["file_data_buffer"]).hexdigest()
        
        if received_file_hash == session_state["expected_hash"]:
            # Si les hash correspondent, sauvegardez le fichier
            with open(file_path, "wb") as file:
                file.write(session_state["file_data_buffer"])
            print("File transfer complete. Hash verified successfully.")
            ack_message = Message("ACK", message.sequence_num, "EOF received. Hash match.")
        else:
            # Si les hash ne correspondent pas, signalez une erreur
            print("File transfer error: Hash mismatch.")
            ack_message = Message("ERROR", message.sequence_num, "EOF received. Hash mismatch.")
        
        # client_socket.send(ack_message.serialize())
        self.send_message(client_socket, ack_message)
        print(f"[ACK] for EOF segment. {len(ack_message.serialize())}")
        session_state["is_uploading"] = False
    
    def handle_handshake(self, client_socket, message, session_state):
        session_state["data_received_size"] = message.content["suggested_size"]
        response = Message("HANDSHAKE_ACK", content={"approved_size": session_state["data_received_size"]})
        # client_socket.send(response.serialize())
        self.send_message(client_socket, response)
        print(f"[HANDSHAKE_ACK] sent with approved size: {session_state['data_received_size']}. {len(response.serialize())}")

    def send_message(self, socket, message):
        serialized_message = message.serialize()
        message_length = len(serialized_message).to_bytes(4, byteorder='big')
        socket.send(message_length + serialized_message)