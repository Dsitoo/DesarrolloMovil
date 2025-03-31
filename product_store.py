import psycopg2
import psycopg2.extras
from database import get_db_connection

class ProductStore:
    def get_all_products(self):
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id, nombre, unidades, costo::numeric(15,2) as costo 
            FROM productos 
            ORDER BY nombre
        """)
        products = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()
        return products

    def add_product(self, nombre, unidades, costo):
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO productos (nombre, unidades, costo)
                VALUES (%s, %s, %s::numeric(15,2))
                RETURNING id
                """,
                (nombre.strip(), int(unidades), float(costo))
            )
            product_id = cur.fetchone()[0]
            conn.commit()
            return product_id
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if 'unique constraint' in str(e).lower():
                raise Exception("Ya existe un producto con ese nombre")
            raise e
        finally:
            cur.close()
            conn.close()

    def update_product_units(self, nombre, nuevas_unidades):
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE productos 
                SET unidades = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE nombre = %s
                RETURNING unidades
                """,
                (max(0, int(nuevas_unidades)), nombre)
            )
            result = cur.fetchone()
            conn.commit()
            return result[0] if result else None
        finally:
            cur.close()
            conn.close()

    def check_stock(self, nombre, cantidad):
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                "SELECT unidades FROM productos WHERE nombre = %s",
                (nombre,)
            )
            result = cur.fetchone()
            return result and result[0] >= int(cantidad)
        finally:
            cur.close()
            conn.close()
