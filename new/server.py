import socket
import zlib
import hashlib
import subprocess

class Server:
    def __init__(self, host='localhost', port=12349):
        self.host = host
        self.port = port
        self.buffer_size = 16_384

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, self.port))
            s.listen()
            print(f"Server listening on {self.host}:{self.port}")

            while True:
                client_socket, address = s.accept()
                print(f"Connection from {address}")
                try:
                    self.handle_client(client_socket)
                except Exception as e:
                    print(f"Error handling client {address}: {e}")
                finally:
                    client_socket.close()

    def handle_client(self, client_socket):
      """Handle the client: receive file, verify hash, and optionally execute."""
      #Step 1: Receive file metadata
      print("Waiting for file metadata...")

      metadata = client_socket.recv(self.buffer_size).decode()
      file_name, expected_size, expected_hash = metadata.split(':')
      expected_size = int(expected_size)

      print(f"Receiving file metadata: {file_name}, {expected_size} bytes, hash: {expected_hash}")
      
      # step 2: Send ACK for metadata
      client_socket.sendall("ACK".encode())

      # Step 3: Receive file in segments
      received_data = b''
      while True:
        segment = client_socket.recv(self.buffer_size)
        if segment.endswith(b"EOF"):  # Check for end of file signal
          received_data += segment[:-3]  # Exclude EOF marker
          break
        else:
          received_data += segment
        client_socket.sendall("ACK".encode())  # Send ACK for each received segment

      # Verify hash
      actual_hash = hashlib.sha256(received_data).hexdigest()
      if actual_hash != expected_hash:
        client_socket.sendall("HASH_FAIL".encode())
        print("Hash mismatch, file corrupted.")
        return
      else:
        client_socket.sendall("ACK".encode())  # Acknowledge successful file reception
      
      # Decompress received data
      decompressed_data = zlib.decompress(received_data)

      # Save or execute file as needed
      with open(file_name, 'wb') as file:
        file.write(decompressed_data)
      print(f"File {file_name} received and verified successfully.")

if __name__ == "__main__":
    server = Server()
    server.start()