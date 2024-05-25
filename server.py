import socket
import threading

HOST = '127.0.0.1'
PORT = 55555
BUFFER_SIZE = 1024

active_users = {}

def handle_client(conn, addr):
    global active_users
    username = None

    try:
        data = conn.recv(BUFFER_SIZE).decode()
        if data.startswith("$&my_username$&"):
            username = data.split("$&my_username$&")[1]
            active_users[username] = conn
            print(f"{username} connected.")
            send_active_users()
        else:
            print("Invalid username. Closing connection..")

        while True:
            data = conn.recv(BUFFER_SIZE).decode()
            if data.startswith("$&send_message$&"):
                print(f"{username} sending message.")
                parts = data.replace("$&send_message$&", "").split("$&")
                print(parts)
                if len(parts) == 3:
                    recipient = parts[0]
                    message = parts[1]
                    send_message(username, recipient, message)
            else:
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if username in active_users:
            del active_users[username]
            print(f"{username} connection closed")
            send_active_users()

        conn.close()

def send_active_users():
    global active_users
    user_list = "$&active_users$&" + "$&".join(active_users.keys()) + "$&"
    for user, connection in active_users.items():
        try:
            connection.send(user_list.encode())
        except:
            print(f"There was a problem connecting to {user}.")

def send_message(sender, recipient, message):
    global active_users
    if recipient in active_users:
        try:
            connection = active_users[recipient]
            connection.send(f"$&incoming_message$&{sender}$&{message}$&".encode())
            print(f"{sender} -> {recipient}: {message}")
        except:
            print(f"There was a problem connecting to {recipient}.")
    else:
        print(f"{recipient} is not online.")

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    print(f"Server running: {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    main()
