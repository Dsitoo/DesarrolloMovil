import json
import os

class ProductStore:
    def __init__(self):
        self.file_path = 'products.json'
        self.products = self._load_products()

    def _load_products(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return json.load(f)
        # Datos iniciales si no existe el archivo
        default_products = [
            {"nombre": "Google Assistant Nest", "unidades": 15, "costo": 223076},
            {"nombre": "Foco LED RGB Controlado", "unidades": 30, "costo": 61876},
            {"nombre": "Control Remoto Universal", "unidades": 25, "costo": 91636},
            {"nombre": "Adaptador de Corriente", "unidades": 50, "costo": 59396},
            {"nombre": "Cámara IP WIFI 2MP", "unidades": 20, "costo": 90892},
            {"nombre": "Chromecast Serie 3", "unidades": 18, "costo": 223076},
            {"nombre": "Interruptor Sencillo", "unidades": 40, "costo": 123876},
            {"nombre": "Interruptor Doble", "unidades": 35, "costo": 148676},
            {"nombre": "Otros (Personal y CH)", "unidades": 10, "costo": 67402}
        ]
        self._save_products(default_products)
        return default_products

    def _save_products(self, products):
        with open(self.file_path, 'w') as f:
            json.dump(products, f)

    def get_all_products(self):
        return self.products

    def add_product(self, nombre, unidades, costo):
        new_product = {
            "nombre": nombre,
            "unidades": int(unidades),
            "costo": int(costo)
        }
        self.products.append(new_product)
        self._save_products(self.products)

    def update_product_units(self, nombre, nuevas_unidades):
        with open(self.file_path, 'r') as file:
            productos = json.load(file)
        
        for producto in productos:
            if producto['nombre'] == nombre:
                producto['unidades'] = nuevas_unidades
                break
        
        with open(self.file_path, 'w') as file:
            json.dump(productos, file, indent=4)
