import socket
import threading
import time
import random
from datetime import datetime

# Server settings
serverIP = '127.0.0.1'
serverPort = 12000
clients = {}  # Stores client info: {client_socket: {'addr': (ip, port), 'seq': int, 'ack': int, 'sid': str, 'time_remaining': int}}
clients_lock = threading.Lock()
server_running = True

# Send message to a client
def send_message(client_socket, message):
    try:
        client_socket.sendall(message.encode())
        print(f"Sent to {clients[client_socket]['addr']}: {message}")
    except Exception as e:
        print(f"Error sending to {clients[client_socket]['addr']}: {e}")

# Session time management
def manage_session_time():
    while server_running:
        with clients_lock:
            for client_socket in list(clients.keys()):
                client_info = clients[client_socket]
                if client_info['time_remaining'] > 0:
                    client_info['time_remaining'] -= 1
                    send_message(client_socket, f"TIME {client_info['time_remaining']}")
                    send_message(client_socket, f"PARTICIPANTS {len([info for info in clients.values() if info['sid']])}")
                    if client_info['time_remaining'] == 0:
                        send_message(client_socket, "Your session has expired. Disconnecting...")
                        client_socket.close()
                        print(f"Client {client_info['sid']} session expired")
                        del clients[client_socket]
        time.sleep(60)

# Broadcast message to all clients except sender
def broadcast_message(message, sender_socket):
    with clients_lock:
        sender_id = clients.get(sender_socket, {}).get('sid', 'Unknown')
        for client_socket in clients:
            if client_socket != sender_socket:
                send_message(client_socket, f"BROADCAST {sender_id} {message}")

# Handle client connection
def handle_client(client_socket, addr):
    try:
        with clients_lock:
            clients[client_socket] = {
                'addr': addr,
                'seq': random.randint(1000, 10000),
                'ack': 1001,
                'sid': None,
                'time_remaining': random.randint(5, 30)
            }
        print(f"Client connected: {addr}, seq={clients[client_socket]['seq']}, ack={clients[client_socket]['ack']}")

        while True:
            data = client_socket.recv(1024).decode(errors='ignore').strip()
            if not data:
                break
            print(f"Received from {addr}: {data}")
            parts = data.split(" ", 1)
            if parts[0] == "CHECKIN" and len(parts) > 1:
                student_id = parts[1]
                if len(student_id) < 3 or len(student_id) > 10 or not student_id.isalnum():
                    send_message(client_socket, "ERROR Invalid student ID")
                    break
                if any(info['sid'] == student_id for info in clients.values()):
                    send_message(client_socket, "ERROR ID already in use")
                    break
                clients[client_socket]['sid'] = student_id
                send_message(client_socket, f"Welcome, {student_id}! You are connected.")
                send_message(client_socket, f"TIME {clients[client_socket]['time_remaining']}")
                send_message(client_socket, f"PARTICIPANTS {len([info for info in clients.values() if info['sid']])}")
                print(f"Check-in: {student_id} from {addr}")
            elif parts[0] == "MSG" and len(parts) > 1:
                text = parts[1]
                if text == "exit":
                    break
                broadcast_message(text, client_socket)
                print(f"Message from {clients[client_socket]['sid']}: {text}")
    except Exception as e:
        print(f"Error with client {addr}: {e}")
    finally:
        with clients_lock:
            if client_socket in clients:
                print(f"Disconnect: {clients[client_socket]['sid'] or addr}")
                del clients[client_socket]
        client_socket.close()

# Start server
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((serverIP, serverPort))
    server_socket.listen(5)
    print(f"Server is listening on {serverIP}:{serverPort}...")
    
    threading.Thread(target=manage_session_time, daemon=True).start()
    
    while server_running:
        try:
            client_socket, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True).start()
        except Exception as e:
            print(f"Error accepting connection: {e}")
            break
    server_socket.close()

if __name__ == "__main__":
    start_server()