import socket
import zlib
import hashlib
import os


class Server:
    def __init__(
        self,
        host="localhost",
        port=12345,
        buffer_size=16_384,
        save_path="received_files",
    ):
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.save_path = save_path

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"Server listening on {self.host}:{self.port}")

            while True:
                client_socket, address = server_socket.accept()
                print(f"Connection from {address}")
                try:
                    self.handle_client(client_socket)
                except Exception as e:
                    print(f"Error handling client {address}: {e}")
                finally:
                    client_socket.close()

    def handle_client(self, client_socket):
        print("Receiving file metadata...")
        file_name, expected_size, expected_hash = self.receive_metadata(client_socket)
        if not file_name or not expected_size or not expected_hash:
            print("Failed to receive file metadata. Aborting with client.")
            return

        print("Receiving file data...")
        received_data = self.receive_file(client_socket, int(expected_size))
        if not received_data:
            print("Failed to receive file data. Aborting with client.")
            return

        print("Verifying file hash...")
        if not self.verify_hash(client_socket, file_name, expected_hash, received_data):
            print("Failed to verify file hash. Aborting with client.")
            return

        print("Saving file...")
        if self.save_file(file_name, received_data):
            client_socket.sendall("SAVED".encode())

        print(f"File {file_name} received and saved successfully.")

    def receive_metadata(self, client_socket):
        metadata = client_socket.recv(self.buffer_size).decode()
        if not metadata:
            return None, None, None
        file_name, expected_size, expected_hash = metadata.split(":")
        client_socket.sendall("ACK".encode())
        return file_name, expected_size, expected_hash

    def receive_file(self, client_socket, expected_size):
        received_data = b""
        while len(received_data) < expected_size:
            segment = client_socket.recv(self.buffer_size)
            if not segment:
                return None
            received_data += segment
            client_socket.sendall("ACK".encode())
        return received_data

    def verify_hash(self, client_socket, file_name, expected_hash, received_data):
        actual_hash = hashlib.sha256(received_data).hexdigest()
        if actual_hash != expected_hash:
            client_socket.sendall("HASH_FAIL".encode())
            return False
        client_socket.sendall("HASH_OK".encode())
        return True

    def save_file(self, file_name, file_data):
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
        file_path = os.path.join(self.save_path, file_name)
        with open(file_path, "wb") as file:
            file.write(zlib.decompress(file_data))


if __name__ == "__main__":
    server = Server()
    server.start()
