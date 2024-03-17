import socket
import os
import zlib
import hashlib
import time


class Client:
    def __init__(
        self,
        host="localhost",
        port=12345,
        buffer_size=16_384,
        max_retries=5,
        retry_interval=5,
    ):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.max_retries = max_retries
        self.retry_interval = retry_interval

    def connect(self):
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
                print("Connected to server")
                return True
            except Exception as e:
                print(f"Connection failed: {e}")
                retry_count += 1
                print(f"Retrying connection in {self.retry_interval} seconds...")
                time.sleep(self.retry_interval)
        print("Maximum retries reached. Failed to connect to server.")
        return False

    def receive_socket(self, size):
        while True:
            try:
                data = self.sock.recv(size)
                if not data:
                    raise Exception("Connection closed by peer")
                return data
            except Exception as e:
                print(f"Error receiving data: {e}")
                if not self.reconnect():
                    return b""

    def send_socket(self, data):
        while True:
            try:
                self.sock.sendall(data)
                return True
            except Exception as e:
                print(f"Error sending data: {e}")
                if not self.reconnect():
                    return False

    def reconnect(self):
        self.sock.close()
        return self.connect()

    # ----------------- File Transfer ----------------- #

    def compress_and_hash_file(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as file:
            file_data = file.read()
            compressed_data = zlib.compress(file_data)
            sha256_hash.update(compressed_data)
        return compressed_data, sha256_hash.hexdigest()

    def send_file(self, file_path):
        if not self.connect():
            return

        # Step 1: Send file metadata

        file_name = os.path.basename(file_path)
        compressed_file, file_hash = self.compress_and_hash_file(file_path)
        metadata = f"{file_name}:{len(compressed_file)}:{file_hash}"

        if not self.send_socket(metadata.encode()):
            print("Failed to send file metadata, aborting.")
            return

        if self.receive_socket(self.buffer_size).decode() != "ACK":
            print("Server did not ACK file metadata, aborting.")
            return

        print(f"File metadata sent successfully: {metadata}")

        # Step 2: Send file in segments

        if not self.send_segments(compressed_file):
            print("Failed to send file segments, aborting.")
            return

        print("File segments sent successfully.")

    def send_segments(self, compressed_file):
        total_segments = len(compressed_file) // self.buffer_size + (
            1 if len(compressed_file) % self.buffer_size > 0 else 0
        )

        for i in range(total_segments):
            print(f"Sending segment {i+1}/{total_segments}")

            start = i * self.buffer_size
            end = start + self.buffer_size
            segment = compressed_file[start:end]

            if not self.send_socket(segment):
                return False

            # Wait for ACK
            response = self.receive_socket(self.buffer_size).decode()
            if response == b"":  # If the connection is lost
                return False
            elif response != "ACK":
                print("ACK not received, resending segment...")
                if not self.send_socket(segment):
                    return False

        # Indicate end of transmission

        if not self.send_socket("EOF".encode()):
            return False

        # Wait for final file hash verification (HASH_FAIL)

        response = self.receive_socket(self.buffer_size).decode()
        return response == "HASH_OK"

    def send_execution_instruction(self):
        if not self.send_socket("EXECUTE".encode()):
            print("Failed to send EXECUTE instruction, aborting.")
            return

        while True:
            data = self.receive_socket(self.buffer_size).decode()
            if data == "END_EXECUTION":
                break
            print(data)

        print("Execution completed.")


if __name__ == "__main__":
    client = Client(port=12346)
    file = "test.sh"
    file_path = os.path.join(os.path.dirname(__file__), file)

    client.send_file(file_path)
    client.send_execution_instruction()
