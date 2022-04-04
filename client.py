import socket
import threading
import os

# Replace host with server's inet if use vpn
#host = socket.gethostname()
host = "10.27.0.7"
port = 8000
address = (host, port)

client = socket.socket()
client.connect(address)

username = input("Choose a name: ")


def receive():
    while True:
        try:
            msg = message = client.recv(1024).decode()
            
            if ("USERNAME" in message):
                client.send(username.encode())
            elif("FILE TRANSFER -|- FILENAME @ " in message):
                _, part_name, part_content = message.split(" -|- ")
                file_name = os.path.join("download/", part_name.split(" @ ")[1])
                file_content = part_content.split(" @ ")[1]
                with open(file_name, "w") as f:
                    f.write(file_content)
                print("Downloaded file")
            else:
                print(message)
                
        except:
            print("An error occured!")
            client.close()
            break


def write():
    while True:
        message = input(f"")

        if ("/sendfile " in message):    
            _, target, filename = message.split(" ")
            with open(filename, "r") as f:
                file = f.read()
            send_data = f"{file}"
            client.send(f"{username}: {message} -|- {send_data}".encode())
        else:
            client.send(f"{username}: {message}".encode())


receive_thread = threading.Thread(target=receive)
receive_thread.start()

write_thread = threading.Thread(target=write)
write_thread.start()

