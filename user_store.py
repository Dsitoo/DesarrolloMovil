import json
import os

class UserStore:
    def __init__(self):
        self.file_path = 'users.json'
        self.users = self._load_users()
        self._ensure_admin_exists()

    def _ensure_admin_exists(self):
        if not self.users:
            # Crear admin por defecto si no existe ningún usuario
            self.add_user('admin', 'Administrador', 'admin123', 'admin')

    def _load_users(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_users(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.users, f, indent=4)

    def add_user(self, id_number, username, password, role='client'):
        self.users[id_number] = {
            'username': username,
            'password': password,
            'role': role
        }
        self._save_users()

    def validate_user(self, id_number, password):
        if id_number in self.users:
            return self.users[id_number]['password'] == password
        return False

    def get_user_role(self, id_number):
        if id_number in self.users:
            return self.users[id_number]['role']
        return None

    def get_all_users(self):
        return [(id_number, data) for id_number, data in self.users.items()]

    def delete_user(self, id_number):
        if id_number in self.users and id_number != 'admin':
            del self.users[id_number]
            self._save_users()
            return True
        return False

    def update_user(self, id_number, username=None, password=None, role=None):
        if id_number in self.users:
            if username:
                self.users[id_number]['username'] = username
            if password:
                self.users[id_number]['password'] = password
            if role and id_number != 'admin':  # No permitir cambiar el rol del admin
                self.users[id_number]['role'] = role
            self._save_users()
            return True
        return False

    def get_user_data(self, id_number):
        return self.users.get(id_number)
