import socket
import os
import subprocess
import threading

BUFFER_SIZE = 32
BUFFER_FILENAME = 1024
SERVER_IP = 'localhost'
SERVER_PORT = 12346
FILE_FOLDER = "received_files"

def receive_file(connection):
    initial_msg = connection.recv(1024).decode()
    file_name, file_size = initial_msg.split(':')
    file_size = int(file_size)

    connection.sendall("ACK".encode())

    received_size = 0
    with open(os.path.join(FILE_FOLDER, file_name), 'wb') as file:
        while received_size < file_size:
            bytes_read = connection.recv(min(4096, file_size - received_size))
            if not bytes_read:
                break
            file.write(bytes_read)
            received_size += len(bytes_read)

    print(f"Received {file_name}, {received_size} bytes.")
    return received_size == file_size

def execute_file(file_path, connection):
    """Exécute le fichier et envoie la sortie au client."""
    try:
        os.chmod(file_path, 0o755)

        process = subprocess.Popen(file_path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        for line in process.stdout:
            connection.sendall(line.encode())
        
        process.stdout.close()
        process.wait()
    except Exception as e:
        connection.sendall(f"Error executing file: {e}".encode())
    finally:
        connection.sendall("EXECUTION_COMPLETE".encode())

def handle_client(connection):
    file_received = receive_file(connection)
    if not file_received:
        print("Failed to receive file.")
        return

    while True:
        instruction = connection.recv(BUFFER_SIZE).decode()
        last_file_path = os.path.join(FILE_FOLDER, os.listdir(FILE_FOLDER)[-1])
        execution_thread = threading.Thread(target=execute_file, args=(last_file_path, connection))
        if instruction == "EXECUTE":
            execution_thread.start()
        elif instruction == "EXIT":
            break
            

def main():
    if not os.path.exists(FILE_FOLDER):
        os.makedirs(FILE_FOLDER)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('Starting server on port', SERVER_PORT)
    sock.bind((SERVER_IP, SERVER_PORT))
    sock.listen(1)
    
    try:
        while True:
            print('Waiting for connection')
            connection, client_addr = sock.accept()
            try:
                print(f"{client_addr} connected")
                handle_client(connection)
            finally:
                connection.close()
                print('Connection closed')
    finally:
        sock.close()

if __name__ == "__main__":
    main()
