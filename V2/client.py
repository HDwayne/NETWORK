import socket
import os
import hashlib
import threading
import time
from message import Message

class Client:
    def __init__(self, server_address, server_port):
        self.server_address = server_address
        self.server_port = server_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_address, self.server_port))
        self.lock = threading.Lock()
        self.window_size = 5
        self.ack_received = [False] * self.window_size
        self.current_message_size = 1024
        self.waiting_for_handshake = True

    def send_handshake(self, suggested_size):
        handshake_message = Message('HANDSHAKE', content={'suggested_size': suggested_size}).serialize()
        self.sock.send(handshake_message)
        self.waiting_for_handshake = True
        while self.waiting_for_handshake:
            time.sleep(1)

    def send_file(self, file_path):
        file_name = os.path.basename(file_path)
        file_hash = self.calculate_file_hash(file_path)
        upload_message = Message('UPLOAD', content={'file_name': file_name, 'file_hash': file_hash}).serialize()
        self.sock.send(upload_message)

        threading.Thread(target=self.listen_server, daemon=True).start()

        with open(file_path, 'rb') as file:
            segments = file.read()

        base = 0
        next_seq_num = 0
        window_size = self.window_size
        segments_to_send = [segments[i:i+1024] for i in range(0, len(segments), 1024)]

        while base < len(segments_to_send):
            while next_seq_num < base + window_size and next_seq_num < len(segments_to_send):
                segment = segments_to_send[next_seq_num]
                self.send_data(segment, next_seq_num)
                next_seq_num += 1

            if not self.ack_received[base % window_size]:
                next_seq_num = base
            else:
                base += 1

        self.send_eof(next_seq_num)


    def send_data(self, data, sequence_num):
        data_hash = hashlib.sha256(data).hexdigest()
        data_message = Message('DATA', sequence_num, data, data_hash).serialize()

        if self.current_message_size != len(data_message):
            print(f"Data segment size changed from {self.current_message_size} to {len(data_message)}")
            self.current_message_size = len(data_message)
            self.send_handshake(self.current_message_size)

        self.sock.send(data_message)
        print(f"Sent data segment {sequence_num}")


    def send_eof(self, sequence_num):
        eof_message = Message('EOF', sequence_num).serialize()
        self.sock.send(eof_message)
        print(f"Sent EOF segment {sequence_num}")
   
    def listen_server(self):
        while True:
            try:
                # Lecture de la longueur du message (4 bytes)
                message_length_bytes = self.sock.recv(4)
                if message_length_bytes:
                    message_length = int.from_bytes(message_length_bytes, byteorder='big')
                    # Lecture du reste du message en fonction de sa longueur
                    data = self.sock.recv(message_length)
                    if data:
                        ack_message = Message.deserialize(data)
                        print(f"[DEBUG] Received message: {ack_message.type}")
                        if ack_message.type == 'ACK':
                            ack_num = ack_message.sequence_num
                            print(f"ACK received for {ack_num}")
                            self.ack_received[ack_num % self.window_size] = True
                        elif ack_message.type == 'HANDSHAKE_ACK' and self.waiting_for_handshake:
                            self.waiting_for_handshake = False
                            print("Handshake acknowledged.")
                            pass
                        else:
                            print("Unexpected message type.")
                            exit(1)
            except Exception as e:
                print(f"Error listening for messages: {e}")
                break


    def calculate_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def close_connection(self):
        self.sock.close()
        print("Connection closed.")
