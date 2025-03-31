import psycopg2
import psycopg2.extras
from database import get_db_connection

class UserStore:
    def validate_user(self, id_number, password):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM usuarios WHERE id = %s", (id_number,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user and user['password'] == password

    def add_user(self, id_number, username, password, role='client'):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO usuarios (id, username, password, role) VALUES (%s, %s, %s, %s)",
            (id_number, username, password, role)
        )
        conn.commit()
        cur.close()
        conn.close()

    def get_user_role(self, id_number):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT role FROM usuarios WHERE id = %s", (id_number,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user['role'] if user else None

    def get_all_users(self):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM usuarios")
        users = cur.fetchall()
        cur.close()
        conn.close()
        return [(user['id'], user) for user in users]

    def delete_user(self, id_number):
        if id_number != 'admin':
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM usuarios WHERE id = %s", (id_number,))
            conn.commit()
            cur.close()
            conn.close()
            return True
        return False

    def update_user(self, id_number, username=None, password=None, role=None):
        conn = get_db_connection()
        cur = conn.cursor()
        if username:
            cur.execute("UPDATE usuarios SET username = %s WHERE id = %s", (username, id_number))
        if password:
            cur.execute("UPDATE usuarios SET password = %s WHERE id = %s", (password, id_number))
        if role and id_number != 'admin':  # No permitir cambiar el rol del admin
            cur.execute("UPDATE usuarios SET role = %s WHERE id = %s", (role, id_number))
        conn.commit()
        cur.close()
        conn.close()
        return True

    def get_user_data(self, id_number):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT * FROM usuarios WHERE id = %s", (id_number,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
