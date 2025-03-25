import sqlite3
from datetime import datetime
import time
import os

class Database:
    def __init__(self):
        self.db_name = 'colva_app.sqlite3'  # Cambiado de .db a .sqlite3
        
    def _get_connection(self, max_attempts=5):
        """Intenta obtener una conexión con reintentos"""
        attempt = 0
        while attempt < max_attempts:
            try:
                return sqlite3.connect(self.db_name, timeout=20)
            except sqlite3.OperationalError:
                attempt += 1
                time.sleep(1)
        raise Exception("No se pudo conectar a la base de datos después de varios intentos")

    def _execute_with_retry(self, query, params=None):
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            raise Exception(f"Error en la consulta SQL: {str(e)}")
        finally:
            if conn:
                conn.close()

    def _create_tables(self):
        """Crea las tablas necesarias en la base de datos"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        queries = [
            '''CREATE TABLE IF NOT EXISTS "Usuario" (
                "IdUsuario" INTEGER,
                "NumIdentificacion" INTEGER UNIQUE,
                "NombreUsuario" TEXT NOT NULL,
                "Contraseña" TEXT NOT NULL,
                "Rol" TEXT NOT NULL DEFAULT 2 CHECK("Rol" IN ('admin', 'cliente')),
                PRIMARY KEY("IdUsuario" AUTOINCREMENT)
            )''',
            '''CREATE TABLE IF NOT EXISTS "Productos" (
                "IdProducto" INTEGER,
                "NombreProducto" TEXT NOT NULL UNIQUE,
                "UnidadesExistentes" INTEGER NOT NULL CHECK(UnidadesExistentes >= 0),
                "CostoPorUnidad" REAL NOT NULL CHECK(CostoPorUnidad > 0),
                PRIMARY KEY("IdProducto" AUTOINCREMENT)
            )''',
            '''CREATE TABLE IF NOT EXISTS "Cotizaciones" (
                "IdCotizacion" INTEGER,
                "Fecha" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "IdUsuario" INTEGER NOT NULL,
                "Subtotal" REAL NOT NULL,
                "IVA" REAL NOT NULL,
                "Total" REAL NOT NULL,
                PRIMARY KEY("IdCotizacion" AUTOINCREMENT),
                FOREIGN KEY("IdUsuario") REFERENCES "Usuario"("IdUsuario")
            )''',
            '''CREATE TABLE IF NOT EXISTS "CotizacionDetalles" (
                "IdDetalle" INTEGER,
                "IdCotizacion" INTEGER NOT NULL,
                "IdProducto" INTEGER NOT NULL,
                "Cantidad" INTEGER NOT NULL CHECK(Cantidad > 0),
                "PrecioUnitario" REAL NOT NULL,
                "NumeroAmbiente" INTEGER NOT NULL,
                PRIMARY KEY("IdDetalle" AUTOINCREMENT),
                FOREIGN KEY("IdCotizacion") REFERENCES "Cotizaciones"("IdCotizacion"),
                FOREIGN KEY("IdProducto") REFERENCES "Productos"("IdProducto")
            )'''
        ]
        
        try:
            for query in queries:
                cursor.execute(query)
            conn.commit()
        finally:
            conn.close()

    def initialize_database(self):
        """Inicializa la base de datos si no existe"""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            # Crear tablas
            self._create_tables()
            
            # Verificar si las tablas están vacías e insertar datos por defecto
            cursor.execute("SELECT COUNT(*) FROM Usuario")
            if cursor.fetchone()[0] == 0:
                # Insertar usuario administrador y usuarios de ejemplo
                usuarios_default = [
                    (1072649746, "admin", "admin123", "admin"),  # Admin principal
                    (123456789, "Juan Pérez", "juan123", "cliente"),
                    (987654321, "María López", "maria123", "cliente"),
                    (456789123, "Carlos Ruiz", "carlos123", "cliente"),
                    (789123456, "Ana Gómez", "ana123", "cliente"),
                    (321654987, "Pedro Martínez", "pedro123", "cliente")
                ]
                cursor.executemany('''
                    INSERT INTO Usuario (NumIdentificacion, NombreUsuario, Contraseña, Rol)
                    VALUES (?, ?, ?, ?)
                ''', usuarios_default)
                conn.commit()
                print("Usuarios creados exitosamente")

            cursor.execute("SELECT COUNT(*) FROM Productos")
            if cursor.fetchone()[0] == 0:
                productos_default = [
                    ("Google Assistant Nest", 140, 223076),
                    ("Foco LED RGB Controlado", 92, 61876),
                    ("Control Remoto Universal", 106, 91636),
                    ("Adaptador de Corriente", 117, 59396),
                    ("Cámara IP WIFI 2MP", 136, 90892),
                    ("Chromecast Serie 3", 144, 223076),
                    ("Interruptor Sencillo", 116, 123876),
                    ("Interruptor Doble", 122, 148676),
                    ("Otros (Personal y CH)", 250, 67402)
                ]
                cursor.executemany('''
                    INSERT INTO Productos (NombreProducto, UnidadesExistentes, CostoPorUnidad)
                    VALUES (?, ?, ?)
                ''', productos_default)
                conn.commit()
                print("Productos creados exitosamente")
        finally:
            conn.close()

    def get_user_count(self):
        cursor = self._execute_with_retry("SELECT COUNT(*) FROM Usuario")
        return cursor.fetchone()[0]

    def get_product_count(self):
        cursor = self._execute_with_retry("SELECT COUNT(*) FROM Productos")
        return cursor.fetchone()[0]

    # Métodos para usuarios
    def add_user(self, id_number, username, password, role='cliente'):  # Cambiado de 'client' a 'cliente'
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                # Verificar si el usuario ya existe
                cursor.execute('SELECT COUNT(*) FROM Usuario WHERE NumIdentificacion = ?', (id_number,))
                if cursor.fetchone()[0] > 0:
                    raise Exception("Ya existe un usuario con ese número de identificación")
                
                # Si no existe, insertar nuevo usuario
                cursor.execute('''
                    INSERT INTO Usuario (NumIdentificacion, NombreUsuario, Contraseña, Rol)
                    VALUES (?, ?, ?, ?)
                ''', (id_number, username, password, role))
                conn.commit()
                return True
            except sqlite3.Error as e:
                conn.rollback()
                raise Exception(f"Error al crear usuario: {str(e)}")

    def validate_user(self, id_number, password):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT Contraseña 
                FROM Usuario 
                WHERE NumIdentificacion = ?
            ''', (id_number,))
            result = cursor.fetchone()
            return result and result[0] == password

    def get_user_role(self, id_number):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT Rol 
                FROM Usuario 
                WHERE NumIdentificacion = ?
            ''', (id_number,))
            result = cursor.fetchone()
            return result[0] if result else None

    def get_all_users(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT NumIdentificacion, NombreUsuario, Rol 
                FROM Usuario
            ''')
            users = cursor.fetchall()
            return [(user[0], {
                'username': user[1],
                'role': user[2]
            }) for user in users]

    def update_user(self, id_number, username=None, password=None, role=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            values = []
            if username:
                updates.append('NombreUsuario = ?')
                values.append(username)
            if password:
                updates.append('Contraseña = ?')
                values.append(password)
            if role:
                updates.append('Rol = ?')
                values.append(role)
            
            if updates:
                values.append(id_number)
                query = f'''
                    UPDATE Usuario 
                    SET {", ".join(updates)} 
                    WHERE NumIdentificacion = ?
                '''
                cursor.execute(query, values)
                return True
        return False

    def delete_user(self, id_number):
        if id_number == 'admin':
            return False
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM Usuario WHERE NumIdentificacion = ?', (id_number,))
            return cursor.rowcount > 0

    def get_user_data(self, user_id):
        """Obtiene todos los datos de un usuario específico"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT NombreUsuario, Rol
                FROM Usuario 
                WHERE NumIdentificacion = ?
            ''', (user_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'username': result[0],
                    'role': result[1]
                }
            return None

    # Métodos para productos
    def get_all_products(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT NombreProducto, UnidadesExistentes, CostoPorUnidad 
                FROM Productos
            ''')
            products = cursor.fetchall()
            return [{
                'nombre': row[0],
                'unidades': row[1],
                'costo': row[2]
            } for row in products]

    def add_product(self, nombre, unidades, costo):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO Productos (NombreProducto, UnidadesExistentes, CostoPorUnidad)
                VALUES (?, ?, ?)
            ''', (nombre, int(unidades), float(costo)))

    def update_product_units(self, nombre, nuevas_unidades):
        """Actualiza las unidades de un producto validando que no sea negativo"""
        if nuevas_unidades < 0:
            nuevas_unidades = 0
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE Productos 
                SET UnidadesExistentes = ? 
                WHERE NombreProducto = ?
            ''', (int(nuevas_unidades), nombre))
            conn.commit()

    # Métodos para cotizaciones
    def save_cotizacion(self, cliente_data, subtotal, iva, total, detalles):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Insertar cotización
            cursor.execute('''
                INSERT INTO cotizaciones (
                    cliente_tipo_doc, cliente_num_doc, cliente_nombres,
                    cliente_apellidos, cliente_telefono, cliente_email,
                    subtotal, iva, total
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cliente_data['tipo_documento'], cliente_data['numero_documento'],
                cliente_data['nombres'], cliente_data['apellidos'],
                cliente_data['telefono'], cliente_data['email'],
                subtotal, iva, total
            ))
            
            cotizacion_id = cursor.lastrowid
            
            # Insertar detalles
            for ambiente, productos in detalles.items():
                for producto in productos:
                    cursor.execute('''
                        INSERT INTO cotizacion_detalles (
                            cotizacion_id, ambiente, producto_id,
                            cantidad, precio_unitario
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        cotizacion_id, ambiente,
                        self.get_product_id(producto['nombre']),
                        producto['cantidad'], producto['precio']
                    ))

    def get_product_id(self, nombre):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM productos WHERE nombre = ?', (nombre,))
            result = cursor.fetchone()
            return result[0] if result else None
