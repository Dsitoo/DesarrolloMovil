import json
import os

class UserStore:
    def __init__(self):
        self.file_path = 'users.json'
        self.users = self._load_users()

    def _load_users(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_users(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.users, f)

    def add_user(self, id_number, username, password):
        self.users[id_number] = {
            'username': username,
            'password': password
        }
        self._save_users()

    def validate_user(self, id_number, password):
        if id_number in self.users:
            return self.users[id_number]['password'] == password
        return False
