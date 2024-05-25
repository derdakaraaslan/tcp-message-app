from enum import Enum
import sys
import socket
import threading
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QTextEdit, QLineEdit
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from database import MessagingDatabase

class MessageReceiver(QObject):
    message_received = pyqtSignal(str, str, str, MessagingDatabase)
    active_users_updated = pyqtSignal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def receive_messages(self, client_socket, database, username):
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if data.startswith("$&active_users$&"):
                    active_users = data.split("$&active_users$&")[1].split("$&")
                    self.active_users_updated.emit(active_users, username)
                elif data.startswith("$&incoming_message$&"):
                    parts = data.replace("$&incoming_message$&", "").split("$&")
                    sender = parts[0]
                    message = parts[1]
                    self.message_received.emit(sender, message, username, database)
            except Exception as e:
                print(f"Hata: {e}")
                break

class TYPES(Enum):
    GROUP = 1
    USER = 2
    SEARCH = 3

class ChatApplication(QWidget):
    database = None

    def __init__(self):
        super().__init__()

        self.initUI()
        self.username = None
        self.selected_user = None
        self.selected_type = None
        self.selected_group = None

        self.server_host = '127.0.0.1'
        self.server_port = 55555
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def initUI(self):
        main_layout = QHBoxLayout()

        user_and_group_layout = QVBoxLayout()

        self.user_list = QListWidget()
        self.user_list.itemClicked.connect(self.user_clicked)

        add_to_group_button = QPushButton("Add to group")
        add_to_group_button.clicked.connect(self.add_to_group)

        self.group_list = QListWidget()
        self.group_list.itemClicked.connect(self.group_clicked)

        user_and_group_layout.addWidget(self.user_list)
        user_and_group_layout.addWidget(add_to_group_button)
        user_and_group_layout.addWidget(self.group_list)

        message_layout = QVBoxLayout()
        self.messages_display = QTextEdit()
        self.messages_display.setReadOnly(True)
        self.message_input = QTextEdit()
        self.message_input.setFixedHeight(50)
        send_button = QPushButton("Send")
        send_button.clicked.connect(self.send_message)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_button)

        message_layout.addWidget(self.messages_display)
        message_layout.addLayout(input_layout)

        right_layout = QVBoxLayout()

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_button_clicked)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)

        group_layout = QHBoxLayout()
        self.group_input = QLineEdit()
        group_button = QPushButton("Create Group")
        group_button.clicked.connect(self.create_group)
        group_layout.addWidget(self.group_input)
        group_layout.addWidget(group_button)

        connect_layout = QHBoxLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self.connect_to_server)
        connect_layout.addWidget(self.username_input)
        connect_layout.addWidget(connect_button)

        right_layout.addLayout(connect_layout)
        right_layout.addLayout(search_layout)
        right_layout.addLayout(group_layout)

        main_layout.addLayout(user_and_group_layout)
        main_layout.addLayout(message_layout)
        main_layout.addLayout(right_layout)

        self.setLayout(main_layout)
        self.setWindowTitle('TCP Chat Application')
        self.setGeometry(100, 100, 800, 600)
        self.show()
        

    def connect_to_server(self):
        if not self.client_socket:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((self.server_host, self.server_port))
            self.client_socket.send(f"$&my_username$&{self.username_input.text()}".encode())
            self.username = self.username_input.text()
            ChatApplication.database = MessagingDatabase(username=self.username)
            self.refresh_groups()
            self.get_messaged_users()
            threading.Thread(target=self.receive_messages, 
                             kwargs={'client_socket': self.client_socket, 'database': ChatApplication.database, 'username': self.username}).start()
        except Exception as e:
            print(f"Hata: {e}")

    def create_group(self):
        if not self.group_input.text():
            return
        group_name = self.group_input.text()
        ChatApplication.database.create_group(group_name)
        self.refresh_groups()

    def add_to_group(self):
        if not self.selected_group or not self.selected_user:
            return
        ChatApplication.database.add_user_to_group(self.selected_group, self.selected_user)
        self.refresh_groups()

    def receive_messages(self, client_socket, database, username):
        message_receiver = MessageReceiver()
        message_receiver.message_received.connect(self.handle_message_received)
        message_receiver.active_users_updated.connect(self.handle_active_users_updated)
        message_receiver.receive_messages(client_socket, database, username)

    def handle_message_received(self, sender, message, username, database):
        database.add_message(sender, username, message)
        self.refresh_messages()

    def handle_active_users_updated(self, active_users, username):
        self.user_list.clear()
        if username in active_users:
            active_users.remove(username)
        self.user_list.addItems(active_users)
        self.get_messaged_users()

    def user_clicked(self, item):
        self.selected_type = TYPES.USER
        recipient = item.text()
        self.selected_user = recipient
        self.refresh_messages()

    def group_clicked(self, item):
        self.selected_type = TYPES.GROUP
        group_name = item.text()
        self.selected_group = group_name.split("\n")[0]
        self.refresh_messages()

    def refresh_messages(self):
        if self.selected_type == TYPES.USER:
            self.refresh_user_messages()
        elif self.selected_type == TYPES.GROUP:
            self.refresh_group_messages()
        elif self.selected_type == TYPES.SEARCH:
            self.search_messages()

    def refresh_user_messages(self):
        if self.selected_user:
            messages = ChatApplication.database.get_messages(self.selected_user, self.username)
            if messages is None:
                return
            self.messages_display.clear()
            for sender, message, timestamp in messages:
                self.messages_display.append(f"{sender}: {message} ({timestamp})")

    def refresh_group_messages(self):
        if self.selected_group:
            messages = ChatApplication.database.get_group_messages(self.selected_group)
            if messages is None:
                return
            self.messages_display.clear()
            for sender, message, timestamp in messages:
                self.messages_display.append(f"{sender}: {message} ({timestamp})")

    def refresh_groups(self):
        groups = ChatApplication.database.get_groups_with_member()
        self.group_list.clear()
        for group, members in groups.items():
            if members is None:
                members = []
            while None in members:
                members.remove(None)
            members_str = f"{group}\n\t("+", ".join(members)+ ")"
            self.group_list.addItem(members_str)
        
    def send_message(self):
        if self.selected_type == TYPES.USER:
            self.send_user_message()
        elif self.selected_type == TYPES.GROUP:
            self.send_group_message()

    def send_user_message(self):
        message = self.message_input.toPlainText()
        ChatApplication.database.add_message(self.username, self.selected_user, f"{message}")
        self.message_input.clear()
        self.client_socket.send(f"$&send_message$&{self.selected_user}$&{message}$&".encode())
        self.refresh_messages()

    def send_group_message(self):
        message = self.message_input.toPlainText()
        ChatApplication.database.add_group_message(self.selected_group, self.username, f"{message}")
        self.message_input.clear()
        group_members = ChatApplication.database.get_group_members(self.selected_group)
        for member in group_members:
            self.client_socket.send(f"$&send_message$&{member}$&{message}$&".encode())
        self.refresh_messages()

    def search_button_clicked(self):
        self.selected_type = TYPES.SEARCH
        self.refresh_messages()

    def search_messages(self):
        keyword = self.search_input.text()
        messages = ChatApplication.database.search_messages(keyword)
        self.messages_display.clear()
        for sender, receiver, group_name, message, timestamp in messages:
            if receiver:
                self.messages_display.append(f"{sender} -> {receiver} ({timestamp}): {message}")
            elif group_name:
                self.messages_display.append(f"{sender} -> {group_name} ({timestamp}): {message}")

    def get_messaged_users(self):
        users = ChatApplication.database.get_messaged_users()
        if users is None:
            return
        if self.username in users:
            users.remove(self.username)
        for user in users:
            if self.user_list.findItems(user, Qt.MatchExactly):
                continue
            self.user_list.addItem(user)

    def closeEvent(self, event):
        if self.client_socket:
            self.client_socket.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ChatApplication()
    sys.exit(app.exec_())
