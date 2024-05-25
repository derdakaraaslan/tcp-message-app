import sqlite3
import os

class MessagingDatabase:
    def __init__(self, username, db_name='messaging.db'):
        self.username = username
        if not os.path.exists(username):
            os.makedirs(username)

        self.conn = sqlite3.connect(f'{username}/{db_name}', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS Messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_username TEXT NOT NULL,
                receiver_username TEXT,
                message TEXT NOT NULL,
                group_name TEXT,
                timestamp TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS GroupMembers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                FOREIGN KEY (group_id) REFERENCES Groups(id)
            )
        ''')
        self.conn.commit()

    def add_message(self, sender, receiver, message):
        self.cursor.execute('''
            INSERT INTO Messages (sender_username, receiver_username, message)
            VALUES (?, ?, ?)
        ''', (sender, receiver, message))
        self.conn.commit()

    def get_messages(self, username1, username2):
        self.cursor.execute('''
            SELECT sender_username, message, timestamp FROM Messages
            WHERE (group_name IS NULL OR group_name = "") AND (sender_username = ? AND receiver_username = ?)
            OR (sender_username = ? AND receiver_username = ?) 
            ORDER BY id
        ''', (username1, username2, username2, username1))
        return self.cursor.fetchall()
    
    def get_messaged_users(self):
        self.cursor.execute('''
            SELECT DISTINCT sender_username, receiver_username FROM Messages
            WHERE group_name IS NULL OR group_name = ""
        ''')
        rows = self.cursor.fetchall()
        users = set()
        for row in rows:
            users.add(row[0])
            users.add(row[1])
        return users

    def create_group(self, group_name):
        self.cursor.execute('''
            INSERT INTO Groups (group_name)
            VALUES (?)
        ''', (group_name,))
        self.conn.commit()
    
    def get_groups(self):
        self.cursor.execute('''
            SELECT group_name FROM Groups
        ''')
        return [group[0] for group in self.cursor.fetchall()]
    
    def get_group_members(self, group_name):
        self.cursor.execute('''
            SELECT username FROM GroupMembers
            JOIN Groups ON Groups.id = GroupMembers.group_id
            WHERE group_name = ?
        ''', (group_name,))
        return [member[0] for member in self.cursor.fetchall()]
    
    def get_groups_with_member(self):
        self.cursor.execute('''
            SELECT Groups.group_name, GroupMembers.username 
            FROM Groups 
            LEFT JOIN GroupMembers ON Groups.id = GroupMembers.group_id
        ''')
        rows = self.cursor.fetchall()
        
        groups_with_member = {}
        for row in rows:
            group_name = row[0]
            member = row[1]
            
            if group_name not in groups_with_member:
                groups_with_member[group_name] = [member]
            else:
                groups_with_member[group_name].append(member)
        
        return groups_with_member

    
    def get_group_messages(self, group_name):
        self.cursor.execute('''
            SELECT sender_username, message, timestamp FROM Messages
            WHERE group_name = ?
            ORDER BY id
        ''', (group_name,))
        return self.cursor.fetchall()
    
    def add_group_message(self, group_name, sender, message):
        self.cursor.execute('''
            INSERT INTO Messages (sender_username, group_name, message)
            VALUES (?, ?, ?)
        ''', (sender, group_name, message))
        self.conn.commit()
    
    def add_user_to_group(self, group_name, username):
        self.cursor.execute('''
            SELECT id FROM Groups WHERE group_name = ?
        ''', (group_name,))
        group_id = self.cursor.fetchone()
        if group_id:
            self.cursor.execute('''
                INSERT INTO GroupMembers (group_id, username)
                VALUES (?, ?)
            ''', (group_id[0], username))
            self.conn.commit()
        else:
            raise ValueError(f"Group '{group_name}' not found")

    def search_messages(self, keyword):
        self.cursor.execute('''
            SELECT sender_username, receiver_username, group_name, message, timestamp FROM Messages
            WHERE message LIKE ?
        ''', ('%' + keyword + '%',))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
