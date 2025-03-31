import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME'),
    'port': int(os.getenv('DB_PORT')),
    'sslmode': 'require'
}

class Database:
    def __init__(self):
        self.config = DB_CONFIG

    def _get_connection(self):
        return psycopg2.connect(**self.config)

    def _execute_query(self, query, params=None, fetch=False):
        conn = None
        try:
            conn = self._get_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            cur.execute(query, params)
            
            if fetch:
                result = cur.fetchall()
            else:
                result = cur.rowcount
                
            conn.commit()
            return [dict(row) for row in result] if fetch else result
        except psycopg2.IntegrityError as e:
            if conn:
                conn.rollback()
            if 'unique constraint' in str(e).lower():
                # Verificar si es un error de usuario
                if 'usuarios_pkey' in str(e).lower() or 'usuarios_id_key' in str(e).lower():
                    raise Exception("Ya existe un usuario con este número de identificación")
                # Si no es usuario, entonces es producto
                raise Exception("Ya existe un producto con ese nombre")
            elif 'check constraint' in str(e).lower():
                raise Exception("Valor fuera de rango permitido")
            raise Exception(f"Error de integridad: {str(e)}")
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            raise Exception(f"Error en la base de datos: {str(e)}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    def initialize_database(self):
        try:
            # Crear tablas si no existen (sin DROP)
            self._execute_query("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INT PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'client'))
                )
            """)
            
            # Crear tabla productos si no existe (sin DROP)
            self._execute_query("""
                CREATE TABLE IF NOT EXISTS productos (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(255) UNIQUE NOT NULL,
                    unidades INT NOT NULL CHECK (unidades >= 0),
                    costo NUMERIC(15,2) NOT NULL CHECK (costo > 0)
                )
            """)

            # Crear tabla cotizaciones
            self._execute_query("""
                CREATE TABLE IF NOT EXISTS cotizaciones (
                    id SERIAL PRIMARY KEY,
                    usuario_id INT NOT NULL,
                    fecha TIMESTAMP DEFAULT NOW(),
                    cliente_tipo_doc VARCHAR(50) NOT NULL,
                    cliente_num_doc VARCHAR(50) NOT NULL,
                    cliente_nombres VARCHAR(255) NOT NULL,
                    cliente_apellidos VARCHAR(255) NOT NULL,
                    cliente_telefono VARCHAR(50) NOT NULL,
                    cliente_email VARCHAR(255) NOT NULL,
                    subtotal NUMERIC(10,2) NOT NULL,
                    iva NUMERIC(10,2) NOT NULL,
                    total NUMERIC(10,2) NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                )
            """)

            # Crear tabla cotizacion_detalles
            self._execute_query("""
                CREATE TABLE IF NOT EXISTS cotizacion_detalles (
                    id SERIAL PRIMARY KEY,
                    cotizacion_id INT NOT NULL,
                    ambiente INT NOT NULL,
                    producto_id INT NOT NULL,
                    cantidad INT NOT NULL,
                    precio_unitario NUMERIC(10,2) NOT NULL,
                    FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id),
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

            # Verificar usuarios existentes
            users = self._execute_query('SELECT * FROM usuarios', fetch=True)
            if not users:
                admin_user = {
                    "id": 1072649746,
                    "username": "admin",
                    "password": "admin123",
                    "role": "admin"
                }
                self._execute_query(
                    'INSERT INTO usuarios (id, username, password, role) VALUES (%s, %s, %s, %s)',
                    (admin_user['id'], admin_user['username'], admin_user['password'], admin_user['role'])
                )

            # Verificar si hay productos
            products = self._execute_query('SELECT * FROM productos', fetch=True)
            if not products:  # Solo insertar productos por defecto si no hay ninguno
                productos_default = [
                    {
                        "nombre": "Google Assistant Nest",
                        "unidades": 140,
                        "costo": 223076.00
                    },
                    {
                        "nombre": "Foco LED RGB Controlado",
                        "unidades": 30,
                        "costo": 61876.00
                    },
                    {
                        "nombre": "Control Remoto Universal",
                        "unidades": 25,
                        "costo": 91636.00
                    }
                ]
                
                for producto in productos_default:
                    try:
                        self._execute_query(
                            'INSERT INTO productos (nombre, unidades, costo) VALUES (%s, %s, %s)',
                            (producto['nombre'], producto['unidades'], float(producto['costo']))
                        )
                    except Exception as e:
                        print(f"Error insertando producto {producto['nombre']}: {str(e)}")
                        continue

        except Exception as e:
            print(f"Error en inicialización: {str(e)}")
            raise

    def validate_user(self, id_number, password):
        query = 'SELECT * FROM usuarios WHERE id = %s'
        users = self._execute_query(query, (id_number,), fetch=True)
        return users and users[0]['password'] == password

    def get_user_role(self, id_number):
        query = 'SELECT role FROM usuarios WHERE id = %s'
        users = self._execute_query(query, (id_number,), fetch=True)
        return users[0]['role'] if users else None

    def get_user_data(self, id_number):
        """Obtener datos completos de un usuario"""
        query = 'SELECT * FROM usuarios WHERE id = %s'
        users = self._execute_query(query, (id_number,), fetch=True)
        return users[0] if users else None

    def get_all_users(self):
        query = 'SELECT * FROM usuarios'
        users = self._execute_query(query, fetch=True)
        return [(str(user['id']), {
            'username': user['username'],
            'role': user['role']
        }) for user in users]

    def get_all_products(self):
        """Obtener todos los productos con manejo de errores mejorado"""
        try:
            query = """
                SELECT id, nombre, unidades, costo::numeric(15,2) as costo
                FROM productos
                ORDER BY nombre
            """
            return self._execute_query(query, fetch=True)
        except Exception as e:
            print(f"Error obteniendo productos: {str(e)}")
            return []

    def add_product(self, nombre, unidades, costo):
        """Agregar producto con validaciones mejoradas"""
        try:
            # Validar nombre
            if not nombre or not nombre.strip():
                raise ValueError("El nombre no puede estar vacío")
            
            # Validar unidades
            try:
                unidades = int(unidades)
                if unidades < 0:
                    raise ValueError("Las unidades deben ser un número positivo")
            except (ValueError, TypeError):
                raise ValueError("Las unidades deben ser un número entero positivo")
            
            # Validar costo
            try:
                costo = float(costo)
                if costo <= 0:
                    raise ValueError("El costo debe ser mayor que 0")
                if costo >= 1e13:  # 10 trillones como límite práctico
                    raise ValueError("El costo es demasiado grande (máximo permitido: 9,999,999,999.99)")
            except (ValueError, TypeError):
                raise ValueError("El costo debe ser un número válido")

            query = """
                INSERT INTO productos (nombre, unidades, costo)
                VALUES (%s, %s, %s::numeric(15,2))
                RETURNING id, nombre, costo
            """
            
            result = self._execute_query(query, 
                                      (nombre.strip(), unidades, costo), 
                                      fetch=True)
            
            if result:
                print(f"Producto agregado exitosamente: {result[0]}")
                return result[0]['id']
            raise Exception("No se pudo agregar el producto")
            
        except psycopg2.errors.NumericValueOutOfRange:
            raise ValueError("El costo excede el límite permitido (máximo: 9,999,999,999.99)")
        except psycopg2.errors.UniqueViolation:
            raise ValueError(f"Ya existe un producto con el nombre '{nombre}'")
        except Exception as e:
            raise Exception(f"Error agregando producto: {str(e)}")

    def update_product_units(self, nombre, nuevas_unidades):
        """Actualizar unidades con verificación"""
        try:
            # Primero verificamos si el producto existe
            check_query = "SELECT id FROM productos WHERE nombre = %s"
            result = self._execute_query(check_query, (nombre,), fetch=True)
            
            if not result:
                raise Exception(f"No se encontró el producto: {nombre}")

            try:
                nuevas_unidades = int(nuevas_unidades)
                if nuevas_unidades < 0:
                    raise ValueError("Las unidades deben ser un número entero positivo")
            except ValueError:
                raise ValueError("Las unidades deben ser un número entero positivo")

            query = """
                UPDATE productos 
                SET unidades = %s
                WHERE nombre = %s
                RETURNING id, unidades
            """
            result = self._execute_query(query, (nuevas_unidades, nombre), fetch=True)
            
            if not result:
                raise Exception("No se pudo actualizar el producto")
                
            return result[0]['unidades']
            
        except Exception as e:
            raise Exception(f"Error actualizando unidades: {str(e)}")

    def check_stock(self, nombre, cantidad):
        """Verificar stock disponible"""
        try:
            query = "SELECT unidades FROM productos WHERE nombre = %s"
            result = self._execute_query(query, (nombre,), fetch=True)
            
            if not result:
                raise Exception(f"Producto no encontrado: {nombre}")
                
            return result[0]['unidades'] >= int(cantidad)
            
        except Exception as e:
            print(f"Error verificando stock: {str(e)}")
            return False

    def update_user(self, id_number, username=None, password=None, role=None):
        """Actualizar información de usuario con manejo de transacciones"""
        try:
            updates = []
            params = []
            if username:
                updates.append("username = %s")
                params.append(username)
            if password:
                updates.append("password = %s")
                params.append(password)
            if role and str(id_number) != 'admin':
                if role not in ('admin', 'client'):
                    raise ValueError("Rol inválido. Debe ser 'admin' o 'client'")
                updates.append("role = %s")
                params.append(role)

            if not updates:
                return True

            params.append(id_number)
            query = f"""
                UPDATE usuarios 
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id, username, role
            """
            
            result = self._execute_query(query, params, fetch=True)
            if not result:
                raise Exception("Usuario no encontrado")
                
            return result[0]

        except Exception as e:
            raise Exception(f"Error actualizando usuario: {str(e)}")

    def delete_user(self, id_number):
        """Eliminar usuario con validaciones"""
        try:
            if str(id_number) == 'admin':
                raise ValueError("No se puede eliminar el usuario administrador")
                
            query = "DELETE FROM usuarios WHERE id = %s RETURNING id"
            result = self._execute_query(query, (id_number,), fetch=True)
            
            if not result:
                raise Exception("Usuario no encontrado")
                
            return True
        except Exception as e:
            raise Exception(f"Error eliminando usuario: {str(e)}")

    def add_user(self, id_number, username, password, role='client'):
        """Agregar nuevo usuario con validaciones"""
        try:
            if not username or not password:
                raise ValueError("Username y password son requeridos")
                
            if role not in ('admin', 'client'):
                raise ValueError("Rol inválido. Debe ser 'admin' o 'client'")
                
            query = """
                INSERT INTO usuarios (id, username, password, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id, username, role
            """
            result = self._execute_query(
                query, 
                (id_number, username, password, role),
                fetch=True
            )
            return result[0] if result else None
            
        except psycopg2.IntegrityError as e:
            if 'unique constraint' in str(e).lower():
                raise Exception("Ya existe un usuario con este número de identificación")
            raise Exception(f"Error de integridad en la base de datos")
        except Exception as e:
            raise Exception(f"Error agregando usuario: {str(e)}")

    def create_cotizacion(self, usuario_id, cliente_data, valores):
        """Crear cotización incluyendo el ID del usuario"""
        try:
            query = """
                INSERT INTO cotizaciones (
                    usuario_id, cliente_tipo_doc, cliente_num_doc,
                    cliente_nombres, cliente_apellidos, cliente_telefono,
                    cliente_email, subtotal, iva, total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            params = (
                usuario_id,
                cliente_data['tipo_documento'],
                cliente_data['numero_documento'],
                cliente_data['nombres'],
                cliente_data['apellidos'],
                cliente_data['telefono'],
                cliente_data['email'],
                valores['subtotal'],
                valores['iva'],
                valores['total']
            )
            result = self._execute_query(query, params, fetch=True)
            return result[0]['id'] if result else None
            
        except Exception as e:
            raise Exception(f"Error creando cotización: {str(e)}")

    def create_cotizacion_with_details(self, usuario_id, cliente_data, valores, detalles_ambientes):
        """Crear cotización con sus detalles por ambiente"""
        try:
            # Primero crear la cotización
            cotizacion_query = """
                INSERT INTO cotizaciones (
                    usuario_id, cliente_tipo_doc, cliente_num_doc,
                    cliente_nombres, cliente_apellidos, cliente_telefono,
                    cliente_email, subtotal, iva, total
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            params = (
                usuario_id,
                cliente_data['tipo_documento'],
                cliente_data['numero_documento'],
                cliente_data['nombres'],
                cliente_data['apellidos'],
                cliente_data['telefono'],
                cliente_data['email'],
                valores['subtotal'],
                valores['iva'],
                valores['total']
            )
            result = self._execute_query(cotizacion_query, params, fetch=True)
            cotizacion_id = result[0]['id']

            # Luego insertar los detalles por ambiente
            for ambiente_num, productos in detalles_ambientes.items():
                for producto_id, detalle in productos.items():
                    detalle_query = """
                        INSERT INTO cotizacion_detalles (
                            cotizacion_id, ambiente, producto_id,
                            cantidad, precio_unitario
                        ) VALUES (%s, %s, %s, %s, %s)
                    """
                    self._execute_query(
                        detalle_query,
                        (cotizacion_id, ambiente_num, producto_id,
                         detalle['cantidad'], detalle['precio_unitario'])
                    )

            return cotizacion_id
            
        except Exception as e:
            raise Exception(f"Error creando cotización: {str(e)}")

def test_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        print(f"✅ Conexión exitosa a PostgreSQL: {version[0]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

if __name__ == '__main__':
    test_connection()
