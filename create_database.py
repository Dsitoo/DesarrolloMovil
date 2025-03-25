import sqlite3
import os
import json

def create_database():
    db_name = 'colva_app.sqlite3'  # Cambiado de .db a .sqlite3
    
    # Eliminar base de datos si existe
    if os.path.exists(db_name):
        os.remove(db_name)

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Crear tablas
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'client'))
        );

        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            unidades INTEGER NOT NULL CHECK(unidades >= 0),
            costo REAL NOT NULL CHECK(costo > 0)
        );

        CREATE TABLE IF NOT EXISTS cotizaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
            cliente_tipo_doc TEXT NOT NULL,
            cliente_num_doc TEXT NOT NULL,
            cliente_nombres TEXT NOT NULL,
            cliente_apellidos TEXT NOT NULL,
            cliente_telefono TEXT NOT NULL,
            cliente_email TEXT NOT NULL,
            subtotal REAL NOT NULL,
            iva REAL NOT NULL,
            total REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cotizacion_detalles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cotizacion_id INTEGER,
            ambiente INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            FOREIGN KEY(cotizacion_id) REFERENCES cotizaciones(id),
            FOREIGN KEY(producto_id) REFERENCES productos(id)
        );
    ''')

    # Importar usuarios desde users.json
    if os.path.exists('users.json'):
        with open('users.json', 'r') as f:
            users = json.load(f)
            for user_id, user_data in users.items():
                cursor.execute('''
                    INSERT INTO usuarios (id, username, password, role)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, user_data['username'], user_data['password'], user_data['role']))

    # Importar productos desde products.json
    if os.path.exists('products.json'):
        with open('products.json', 'r') as f:
            products = json.load(f)
            for product in products:
                cursor.execute('''
                    INSERT INTO productos (nombre, unidades, costo)
                    VALUES (?, ?, ?)
                ''', (product['nombre'], product['unidades'], product['costo']))

    # Asegurar que existe el usuario admin
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (id, username, password, role)
        VALUES ('admin', 'Administrador', 'admin123', 'admin')
    ''')

    conn.commit()
    conn.close()
    print(f"Base de datos '{db_name}' creada exitosamente.")

if __name__ == '__main__':
    create_database()
