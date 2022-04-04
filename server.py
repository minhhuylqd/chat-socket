import threading
import socket
import time
import os
import math

addr = ("", 8000)

if socket.has_dualstack_ipv6():
    server = socket.create_server(addr, family=socket.AF_INET6, dualstack_ipv6=True, reuse_port=True)
else:
    server = socket.create_server(addr, reuse_port=True)

server.listen(500)

class Client:
    def __init__(self):
        self.client = socket.socket
        self.is_online = False
        self.last_online = 0.0
        self.queue_messages = []

    def __init__(self, client):
        self.client = client

class Group:
    def __init__(self):
        self.host = ""
        self.members = []
        self.ban = []

class QueueMessage:
    def __init__(self):
        self.sender = None
        self.group = None
        self.timestamp = None
        self.context = None
        
class File:
    def __init__(self):
        self.sender = None
        self.target = None
        self.filename = None


user_db = {}
group_db = {}
file_db = {}


def broadcast(message):
    for user in user_db:
        if user_db[user].is_online:
            user_db[user].client.send(message)


def direct_message(message, target):
    if target in user_db:
        user_db[target].client.send(message.encode())


def group_message(message, sender, group_name):
    read_lst = []
    msg_time = time.time()
    for member in group_db[group_name].members:
        if user_db[member].is_online:
            user_db[member].client.send(f"{msg_time} - {group_name} - {sender}: {message}".encode())
            if (member != sender):
                read_lst.append(member)
        else:
            queue_message = QueueMessage()
            queue_message.sender = sender
            queue_message.group = group_name
            queue_message.timestamp = msg_time
            queue_message.context = message
            user_db[member].queue_messages.append(queue_message)
    read_str = ", ".join(read_lst)
    direct_message(f"\n{read_str} have read", sender)
        

# Handle client msg
### - Received client msg
### - Broadcast to target client
def handle(username, client):
    while True:
        global user_db
        global group_db
        try:
            if user_db[username].is_online:
                user_db[username].last_online = time.time()

            recv_message = client.recv(1024).decode()
            try:
                sender, message = recv_message.split(": ")
            except:
                sender = username
                message = recv_message


            ## Region Direct Message
            if (message.startswith("/chat ")):
                command, target = message.split(" ")
                if (target not in user_db):
                    client.send("Targetted user does not exist".encode())
                    continue
                elif (target == sender):
                    client.send("Don't try to spike me".encode())
                else:
                    while True:
                        next_message = client.recv(1024).decode()
                        _, next_context = next_message.split(": ")
                        if (next_context.startswith("/endchat")):
                            break
                        msg_time = time.time()

                        direct_message(f"{msg_time} - {sender}: {next_context}", sender)
                        ### Target is online
                        if (user_db[target].is_online):
                            direct_message(f"{msg_time} - {sender}: {next_context}", target)
                            direct_message(f"\n{msg_time} - {target} has read the message", sender)
                        ### Target is offline
                        else:
                            queue_message = QueueMessage()
                            queue_message.sender = sender
                            queue_message.timestamp = msg_time
                            queue_message.context = next_context
                            user_db[target].queue_messages.append(queue_message)
                            offline_time = math.ceil((msg_time - user_db[target].last_online) / 60.0)
                            direct_message(f"\n{msg_time} - {target} last online {offline_time} minutes ago", sender)

            ## Endregion Direct Message

            ## Region Group Message
            ### Create Group
            elif (message.startswith("/creategroup")):
                command, group_name = message.split(" ")
                if ((group_name not in group_db) and (group_name not in user_db)):
                    group_db[group_name] = Group()
                    group_db[group_name].host = sender
                    group_db[group_name].members.append(sender)
                    client.send(f"Group {group_name} is created successfully!".encode())
                else:
                    client.send(f"The name {group_name} is not unique. Another name please!".encode())

            ### Rename Group
            elif (message.startswith("/renamegroup")):
                command, group_name, new_group_name = message.split(" ")
                if group_name in group_db:
                    if group_db[group_name].host == sender:
                        if ((new_group_name not in group_db) and (new_group_name not in user_db)):
                            group_db[new_group_name] = group_db.pop(group_name)
                            client.send(f"Group {group_name} is renamed to {new_group_name} successfully!".encode())
                        else:
                            client.send(f"The name {new_group_name} is not unique. Another name please!".encode())
                    else:
                        client.send(f"You are not authorized to do so".encode())
                else:
                    client.send(f"Group {group_name} doesn't exist".encode())

            ### Group Interaction
            elif (message.startswith("/chatgroup")):
                command, group_name = message.split(" ")
                if group_name in group_db:
                    if sender in group_db[group_name].members:
                        while True:
                            next_message = client.recv(1024).decode()
                            _, context = next_message.split(": ")
                            #### Group Management
                            ##### Add Member
                            if (context.startswith("/addmember")):
                                if (group_db[group_name].host == sender):
                                    _, target = context.split(" ")
                                    if target not in group_db[group_name].members:
                                        group_db[group_name].members.append(target)
                                        client.send(f"{target} has been added to the group".encode())
                                        user_db[target].client.send(f"You has been added to group {group_name}".encode())
                                    else:
                                        client.send(f"{target} has already in the group".encode())
                                else:
                                    client.send(f"You are not authorized to do so".encode())
                            ##### Delete Member
                            elif (context.startswith("/delmember")):
                                if (group_db[group_name].host == sender):
                                    _, target = context.split(" ")
                                    if target in group_db[group_name].members:
                                        group_db[group_name].members.remove(target)
                                        client.send(f"{target} has been removed from the group".encode())
                                        user_db[target].client.send(f"You has been removed from group {group_name}".encode())
                                    else:
                                        client.send(f"{target} was not in the group".encode())
                                else:
                                    client.send(f"You are not authorized to do so".encode())
                            #### Group Chat
                            elif (context.startswith("/endchat")):
                                break
                            elif (context.startswith("/info")):
                                print(group_db[group_name].members)
                            else:
                                group_message(context, sender, group_name)
                                
                    else:
                        client.send(f"You are not in group {group_name}".encode())
                else:
                    client.send(f"Group {group_name} doesn't exist".encode())

            ## Endregion Group Message

            ## Region File Interaction

            ### Sendfile - Save file to db
            elif ("/sendfile " in message):
                try:
                    context, file_data = message.split(" -|- ")
                    _, target, filename = context.split(" ")
                    if (target in user_db):
                        filepath = os.path.join("static/", filename)
                        with open(filepath, "w") as f:
                            f.write(file_data)
                        direct_message(f"File transfer successfully", sender)
                        if (user_db[target].is_online):
                            direct_message(f"{time.time()} - {sender} sent you file {filename}", target)
                        else:
                            queue_message = QueueMessage()
                            queue_message.sender = sender
                            queue_message.timestamp = time.time()
                            queue_message.context = f"{sender} sent you file {filename}"
                            user_db[target].queue_messages.append(queue_message)

                        upload_file = File()
                        upload_file.sender = sender
                        upload_file.target = target
                        upload_file.filename = filename

                        file_db[upload_file] = filepath
                    else:
                        direct_message(f"User {target} does not exist", sender)


                except Exception as e:
                    client.send("File transfer got some error".encode())
                    print(e)
                
            ### Download file
            elif ("/getfile " in message):
                try:
                    _, file_sender, filename = message.split(" ")
                    file_exist = False
                    for file in file_db:
                        if file.sender == file_sender and file.filename == filename and file.target == username:
                            file_exist = True
                            with open(file_db[file], "r") as f:
                                file_data = f.read()
                            client.send(f"FILE TRANSFER -|- FILENAME @ {filename} -|- FILECONTENT @ {file_data}".encode())
                            print("Sent file")
                            break
                    if not file_exist:
                        direct_message(f"File doesn't exist", username)
                except Exception as e:
                    print("Download File error")
                    print(e)

            
            ## Endregion File Interaction

            else:
                client.send("Command not correct".encode())
        except Exception as e:
            user_db[username].last_online = time.time()
            user_db[username].is_online = False
            user_db[username].client.close()
            print(f"{username} left the chat!")
            print(e)
            broadcast(f"{username} left the chat!".encode())
            break

        

# Receive connection
### - Add client to list + create nickname
def receive():
    while True:
        client, address = server.accept()
        #print(type(client))
        print("Got connect from ", address)
        
        client.send("USERNAME".encode())
        username = client.recv(1024).decode()

        global user_db
        global group_db

        if username not in user_db:
            user_db[username] = Client(client=client)
            user_db[username].is_online = True
            user_db[username].last_online = time.time()
            user_db[username].queue_messages = []
        else:
            user_db[username].client = client
            user_db[username].is_online = True
            user_db[username].last_online = time.time()

        print(f"Client name is {username}")
        broadcast(f"{username} has joined the chat".encode())
        client.send("\nConnected to the server".encode())

        while (user_db[username].queue_messages):
            queue_message = user_db[username].queue_messages.pop(0)
            message_time = math.ceil((time.time() - queue_message.timestamp) / 60.0)
            if (queue_message.group == None):
                client.send(f"\n{message_time} ago - {queue_message.sender}: {queue_message.context}".encode())
            else:
                client.send(f"\n{message_time} ago - {queue_message.group} - {queue_message.sender}: {queue_message.context}".encode())

        thread_handle = threading.Thread(target=handle, args=(username, client,))
        thread_handle.start()


print("Server is listening")
receive()