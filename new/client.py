import socket
import os
import zlib
import hashlib

class Client:
    def __init__(self, host='localhost', port=12349):
        self.host = host
        self.port = port
        self.buffer_size = 16_384

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print("Connected to server")

    def send_file(self, file_path):
        file_size = os.path.getsize(file_path)
        print(f"Sending file: {file_path} of size {file_size} bytes")

        # Step 1: Send file metadata
        file_name = os.path.basename(file_path)
        compressed_file, file_hash = self.compress_and_hash_file(file_path)
        metadata = f"{file_name}:{len(compressed_file)}:{file_hash}"

        print(f"Sending file metadata: {metadata}")
        self.sock.sendall(metadata.encode())

        # Step 2: Wait for server ACK for metadata
        if self.sock.recv(self.buffer_size).decode() != "ACK":
            print("Server did not ACK file metadata, aborting.")
            return
        print("Server ACKed file metadata")
        
        # Step 3: Send file in segments, wait for ACK after each segment
        self.send_segments(compressed_file)

    def compress_and_hash_file(self, file_path):
      """Compress and hash the file, returning the compressed data and its hash."""
      sha256_hash = hashlib.sha256()
      with open(file_path, 'rb') as file:
          file_data = file.read()
          compressed_data = zlib.compress(file_data)
          sha256_hash.update(compressed_data)
      return compressed_data, sha256_hash.hexdigest()

    def send_segments(self, compressed_file):
        print("Sending file segments...")
        segment_size = self.buffer_size
        total_segments = len(compressed_file) // segment_size + (1 if len(compressed_file) % segment_size > 0 else 0)

        for i in range(total_segments):
            print(f"Sending segment {i+1}/{total_segments}")
            start = i * segment_size
            end = start + segment_size
            segment = compressed_file[start:end]
            self.sock.sendall(segment)

            # Wait for ACK
            if self.sock.recv(self.buffer_size).decode() != "ACK":
                print("Segment transmission failed, resending...")
                self.sock.sendall(segment)  # Resend segment in case of failure

        # Indicate end of transmission
        self.sock.sendall("EOF".encode())
        # Wait for final file hash verification ACK
        if self.sock.recv(self.buffer_size).decode() == "HASH_FAIL":
            print("File transmission failed, hash mismatch.")
        else:
            print("File sent successfully.")

if __name__ == "__main__":
    client = Client()
    file = "dummyData.bin"
    file_path = os.path.join(os.path.dirname(__file__), file)

    client.connect()
    client.send_file(file_path)