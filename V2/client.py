import socket
import os
import hashlib
import threading
import time
from message import Message

class Client:
    def __init__(self, server_address, server_port, window_size=10, segment_size=2048):
        self.server_address = server_address
        self.server_port = server_port
        self.window_size = window_size
        self.segment_size = segment_size
        
        self._sock = None
        self._last_ack_received = 0
        self._transmission_status = "NOT_STARTED" # NOT_STARTED, IN_PROGRESS, SUCCESS, FAILED, ERROR

        self._connect()

    # ---------------------------- PUBLIC METHODS ------------------------------

    def send_file(self, file_path):
        self._transmission_status = "IN_PROGRESS"
        threading.Thread(target=self._listen_server, daemon=True).start()
        
        self._send_upload(file_path)

        with open(file_path, 'rb') as file:
            segments = file.read()

        segments_to_send = [segments[i:i+self.segment_size] for i in range(0, len(segments), self.segment_size)]

        seq_num = 0
        while seq_num < len(segments_to_send):
            if seq_num < self._last_ack_received + self.window_size:
                self._send_data(segments_to_send[seq_num], seq_num)
                seq_num += 1
            else:
                time.sleep(0.1)

        self._send_eof()

        while self._transmission_status == "IN_PROGRESS":
            time.sleep(0.1)

        print(f"Transmission status: {self._transmission_status}")

    # ---------------------------- PRIVATE METHODS -----------------------------
    
    def _connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        for attempt in range(5):
            try:
                self._sock.connect((self.server_address, self.server_port))
                print("[client] Connecté avec succès au serveur.")
                break 
            except socket.error as e:
                print(f"[client] Échec de la connexion au serveur, tentative {attempt + 1}/5")
                if attempt < 4:
                    time.sleep(2)
                else:
                    print("[client] Impossible de se connecter au serveur.")
                    exit(1)
    
    def _send_upload(self, file_path):
        file_name = os.path.basename(file_path)
        file_hash = self._calculate_file_hash(file_path)
        upload_message = Message('UPLOAD', content={'file_name': file_name, 'file_hash': file_hash})
        self._send_message(upload_message)
        print(f"[UPLOAD] Sent upload message for {file_name}")

    def _send_data(self, data, sequence_num):
        data_hash = hashlib.sha256(data).hexdigest()
        data_message = Message('DATA', sequence_num, data, data_hash)
        self._send_message(data_message)
        print(f"[DATA  ] Sent data segment {sequence_num}")

    def _send_eof(self):
        eof_message = Message('EOF')
        self._send_message(eof_message)
        print(f"[EOF   ] Sent EOF segment")
   
    def _send_message(self, message):
        serialized_message = message.serialize()
        message_length = len(serialized_message).to_bytes(4, byteorder='big')
        self._sock.send(message_length + serialized_message)

    def _calculate_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    # ---------------------------- THREADS -------------------------------------
      
    def _listen_server(self):
        while True:
            try:
                message_length_bytes = self._sock.recv(4)
                if message_length_bytes:
                    message_length = int.from_bytes(message_length_bytes, byteorder='big')
                    data = self._sock.recv(message_length)
                    if data:
                        ack_message = Message.deserialize(data)
                        if ack_message.type == 'ACK': 
                            print(f"[Server] ACK for segment {ack_message.sequence_num}")
                            self._last_ack_received = max(self._last_ack_received, ack_message.sequence_num)
                        elif ack_message.type == 'NACK':
                            print(f"[Server] NACK for segment {ack_message.sequence_num} : {ack_message.content}")
                            self._last_ack_received = ack_message.sequence_num
                        elif ack_message.type == 'EOF_ACK':
                            print("[Server] EOF ACK")
                            self._transmission_status = "SUCCESS"
                        elif ack_message.type == 'EOF_NACK':
                            print(f"[Server] EOF NACK : {ack_message.content}")
                            self._transmission_status = "FAILED"
                        else:
                            print("[Server] Unexpected message type.")
                            self._transmission_status = "ERROR"
            except Exception as e:
                print(f"Error listening for messages: {e}")
                break
