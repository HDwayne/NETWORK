import socket
import os
import hashlib
import threading
import time
from message import Message

class Client:
    def __init__(self, server_address, server_port, window_size=10, segment_size=2048, timeout=0.5):
        self.server_address = server_address
        self.server_port = server_port
        self.window_size = window_size
        self.segment_size = segment_size
        self.timeout = timeout
        
        self._sock = None
        self._current_base = None
        self._transmission_status = "NOT_STARTED" # NOT_STARTED, IN_PROGRESS, SUCCESS, FAILED
        self._segments_to_send = None
        self._retransmission_in_progress = False
        self._retransmission_lock = threading.Lock()

        self._connect()

    # ---------------------------- PUBLIC METHODS ------------------------------

    def send_file(self, file_path):
        self._transmission_status = "IN_PROGRESS"
        threading.Thread(target=self._listen_server, daemon=True).start()
        
        self._send_upload(file_path)
        
        with open(file_path, 'rb') as file:
            segments = file.read()
        
        self._segments_to_send = [segments[i:i+self.segment_size] for i in range(0, len(segments), self.segment_size)]
        
        self._current_base = 0
        seq_num = 0
        while seq_num < len(self._segments_to_send):
            with self._retransmission_lock:
                if not self._retransmission_in_progress and seq_num <= self._current_base + self.window_size - 1:
                    self._send_data(self._segments_to_send[seq_num], seq_num)
                    seq_num += 1
                    setattr(self, f"_timer_{seq_num}", threading.Timer(self.timeout, self._check_timeout, args=(seq_num,)))
                    getattr(self, f"_timer_{seq_num}").start()

        self._clear_timers()

        # Attendre que tous les ACKs soient reçus avant de conclure
        while self._current_base < len(self._segments_to_send):
            time.sleep(0.1)


        # DO NOT SENT WHILE LAST SEGMENT IS NOT ACKNOWLEDGED eof
        self._send_eof()
        
        # Attendre que le serveur réponde avec un EOF_ACK ou EOF_NACK
        while self._transmission_status == "IN_PROGRESS":
            time.sleep(0.1)

        self._segments_to_send = None
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

    def _clear_timers(self):
        for i in range(self._current_base):
            if hasattr(self, f"_timer_{i}"):
                getattr(self, f"_timer_{i}").cancel()
                delattr(self, f"_timer_{i}")

    # ---------------------------- THREADS -------------------------------------

    def _check_timeout(self, seq_num):
        with self._retransmission_lock:
            if seq_num > self._current_base and not self._retransmission_in_progress:
                self._clear_timers()
                self._retransmission_in_progress = True

                print(f"[Timeout] detected for segment {seq_num}, initiating retransmission from base {self._current_base}.")
                end_window = min(self._current_base + self.window_size, len(self._segments_to_send))
                for seq_num in range(self._current_base, end_window):
                    print(f"[Timeout] Retransmitting segment {seq_num}")
                    self._send_data(self._segments_to_send[seq_num], seq_num)
                    setattr(self, f"_timer_{seq_num}", threading.Timer(self.timeout, self._check_timeout, args=(seq_num,)))
                    getattr(self, f"_timer_{seq_num}").start()
                
                self._retransmission_in_progress = False

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
                            if hasattr(self, f"_timer_{ack_message.sequence_num}"):
                                getattr(self, f"_timer_{ack_message.sequence_num}").cancel()
                                delattr(self, f"_timer_{ack_message.sequence_num}")
                            self._current_base = max(self._current_base, ack_message.sequence_num + 1)
                        elif ack_message.type == 'EOF_ACK':
                            print("[Server] EOF ACK")
                            self._transmission_status = "SUCCESS"
                        elif ack_message.type == 'EOF_NACK':
                            print(f"[Server] EOF NACK : {ack_message.content}")
                            self._transmission_status = "FAILED"
            except Exception as e:
                print(f"Error listening for messages: {e}")
                break
