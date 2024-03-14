import socket
import os
import time

BUFFER_SIZE = 32
HOST = 'localhost'
PORT = 12346
FILE_FOLDER = "files"
NUMBER_TRY = 5

def connect_to_server(host, port, number_of_tries):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for attempt in range(number_of_tries):
        try:
            sock.connect((host, port))
            print('Connected to server')
            return sock 
        except socket.timeout:
            print(f'Connection attempt {attempt+1} timed out')
        except socket.error as err:
            print(f'Connection attempt {attempt+1} failed: {err}')
        time.sleep(1)
    sock.close()
    print('Connection closed after several attempts')
    return None


def send_file(sock, file_path):
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    sock.sendall(f"{file_name}:{file_size}".encode())

    ack = sock.recv(BUFFER_SIZE).decode()
    if ack != "ACK":
        print("Failed to receive ACK from server, stopping file transfer.")
        return

    with open(file_path, 'rb') as file:
        while True:
            bytes_read = file.read(BUFFER_SIZE)
            if not bytes_read:
                break
            sock.sendall(bytes_read)
    print("File sent successfully.")


def send_execution_instruction(sock):
    sock.sendall("EXECUTE".encode())
    
    while True:
        chunk = sock.recv(BUFFER_SIZE).decode()
        if chunk == "EXECUTION_COMPLETE":
            # send exit instruction
            sock.sendall("EXIT".encode())
            print("EXECUTION_COMPLETE")
            break
        else:
            print(chunk)

def main():
    file_path = os.path.join(FILE_FOLDER, "dummy.sh")
    
    sock = connect_to_server(HOST, PORT, NUMBER_TRY)

    if sock:
        try:
            send_file(sock, file_path)
            time.sleep(1)
            send_execution_instruction(sock)
        finally:
            sock.close()
            print('Connection closed')

if __name__ == '__main__':
    main()