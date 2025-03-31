from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import ObjectProperty, ListProperty
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.recycleview import RecycleView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from functools import partial
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus.flowables import HRFlowable
from datetime import datetime
import os
from kivy.utils import platform
from os.path import expanduser, join
from kivy.uix.modalview import ModalView
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Line
from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton
from kivy.uix.spinner import Spinner
import sqlite3
import traceback
from database import Database

class BaseScreen(Screen):
    def _show_popup(self, title, message, color=(1, 0, 0, 1)):
        content = BoxLayout(orientation='vertical', padding=10)
        label = Label(
            text=message,
            text_size=(280, None),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        label.bind(texture_size=lambda *x: setattr(label, 'height', label.texture_size[1]))
        content.add_widget(label)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(None, None),
            size=(300, label.height + 100),
            auto_dismiss=True
        )
        popup.open()

    def show_error(self, message):
        self._show_popup('Error', message, color=(1, 0, 0, 1))

    def show_success(self, message):
        self._show_popup('Éxito', message, color=(0, 1, 0, 1))

class LoadingScreen(BaseScreen):
    logo = ObjectProperty(None)
    app_name = ObjectProperty(None)
    
    def on_enter(self):
        anim_logo = Animation(opacity=1, duration=2)
        anim_name = Animation(opacity=1, duration=2)
        
        anim_logo.bind(on_complete=self.start_exit_animation)
        anim_name.bind(on_complete=lambda *_: None)
        
        anim_logo.start(self.logo)
        anim_name.start(self.app_name)
    
    def start_exit_animation(self, *args):
        Clock.schedule_once(self.begin_exit, 1)
    
    def begin_exit(self, dt):
        anim_logo = Animation(opacity=0, duration=2)
        anim_name = Animation(opacity=0, duration=2)
        
        anim_logo.bind(on_complete=self.switch_screen)
        anim_name.bind(on_complete=lambda *args: None)
        
        anim_logo.start(self.logo)
        anim_name.start(self.app_name)

    def switch_screen(self, *args):
        self.manager.current = 'login'

class LoginScreen(BaseScreen):
    def validate_login(self, id_number, password):
        if not id_number or not password:
            self.show_error("Por favor complete todos los campos")
            return False
        
        app = App.get_running_app()
        if app.validate_user(id_number, password):
            return True
        
        self.show_error("Identificación o contraseña incorrecta")
        return False

    def on_login_press(self):
        id_number = self.ids.id_input.text
        password = self.ids.password_input.text
        
        if self.validate_login(id_number, password):
            app = App.get_running_app()
            app.current_user_id = id_number
            app.current_user_role = app.get_user_role(id_number)
            print(f"Usuario logueado con rol: {app.current_user_role}")
            self.show_success("Inicio de sesión exitoso")
            self.manager.current = 'principal'

    def on_create_account_press(self):
        self.manager.current = 'register'

class RegisterScreen(BaseScreen):
    def validate_registration(self, username, id_number, password, confirm_password):
        if not all([username, id_number, password, confirm_password]):
            self.show_error("Por favor complete todos los campos")
            return False
        
        if not id_number.isdigit():
            self.show_error("El número de identificación debe contener solo números")
            return False

        if len(id_number) < 8 or len(id_number) > 12:
            self.show_error("El número de identificación debe tener entre 8 y 12 dígitos")
            return False

        if len(password) < 6:
            self.show_error("La contraseña debe tener al menos 6 caracteres")
            return False

        if password != confirm_password:
            self.show_error("Las contraseñas no coinciden")
            return False

        if not username.replace(" ", "").isalpha():
            self.show_error("El nombre solo debe contener letras")
            return False

        return True

    def on_register_press(self):
        username = self.ids.reg_username.text
        id_number = self.ids.reg_id_number.text
        password = self.ids.reg_password.text
        confirm_password = self.ids.reg_confirm_password.text

        if self.validate_registration(username, id_number, password, confirm_password):
            app = App.get_running_app()
            try:
                app.db.add_user(id_number, username, password, 'client')
                self.show_success("Registro exitoso")
                self.manager.current = 'login'
            except Exception as e:
                self.show_error(str(e))

class ProductosRV(RecycleView):
    def __init__(self, **kwargs):
        super(ProductosRV, self).__init__(**kwargs)
        self.load_products()
    
    def load_products(self):
        app = App.get_running_app()
        productos = app.db.get_all_products()
        self.data = [{
            'nombre': p['nombre'],
            'unidades': str(p['unidades']),
            'costo': f"${p['costo']:,}"
        } for p in productos]

class AddProductPopup(Popup):
    def __init__(self, update_callback, **kwargs):
        super().__init__(**kwargs)
        self.update_callback = update_callback
        self.title = 'Agregar Producto'
        self.size_hint = (0.8, 0.6)
        self.content = self.create_content()

    def create_content(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.nombre_input = TextInput(hint_text='Nombre del Producto', multiline=False)
        self.unidades_input = TextInput(hint_text='Unidades', multiline=False)
        self.costo_input = TextInput(hint_text='Costo', multiline=False)
        
        add_button = Button(
            text='Agregar',
            size_hint_y=None,
            height='40dp',
            background_color=(0.2, 0.6, 1, 1)
        )
        add_button.bind(on_press=self.add_product)
        
        layout.add_widget(Label(text='Nombre del Producto'))
        layout.add_widget(self.nombre_input)
        layout.add_widget(Label(text='Unidades'))
        layout.add_widget(self.unidades_input)
        layout.add_widget(Label(text='Costo'))
        layout.add_widget(self.costo_input)
        layout.add_widget(add_button)
        
        return layout

    def add_product(self, instance):
        nombre = self.nombre_input.text.strip()
        unidades = self.unidades_input.text.strip()
        costo = self.costo_input.text.strip()
        
        if not all([nombre, unidades, costo]):
            self.show_error("Todos los campos son requeridos")
            return
            
        if not unidades.isdigit() or not costo.isdigit():
            self.show_error("Unidades y costo deben ser números")
            return
            
        app = App.get_running_app()
        app.db.add_product(nombre, unidades, costo)
        self.update_callback()
        self.dismiss()

    def show_error(self, message):
        content = BoxLayout(orientation='vertical', padding=10)
        label = Label(
            text=message,
            text_size=(280, None),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        label.bind(texture_size=lambda *x: setattr(label, 'height', label.texture_size[1]))
        content.add_widget(label)
        
        popup = Popup(
            title='Error',
            content=content,
            size_hint=(None, None),
            size=(300, label.height + 100),
            auto_dismiss=True
        )
        popup.open()

class SelectProductTypePopup(Popup):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = 'Seleccionar Tipo de Producto'
        self.size_hint = (0.8, 0.4)
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        nuevo_btn = Button(
            text='Nuevo Producto',
            size_hint_y=None,
            height='50dp',
            background_color=(0.2, 0.6, 1, 1)
        )
        nuevo_btn.bind(on_press=lambda x: self.select_type('nuevo'))
        
        existente_btn = Button(
            text='Actualizar Producto Existente',
            size_hint_y=None,
            height='50dp',
            background_color=(0.2, 0.8, 0.2, 1)
        )
        existente_btn.bind(on_press=lambda x: self.select_type('existente'))
        
        layout.add_widget(nuevo_btn)
        layout.add_widget(existente_btn)
        self.content = layout

    def select_type(self, tipo):
        self.dismiss()
        self.callback(tipo)

class UpdateProductPopup(Popup):
    def __init__(self, producto, update_callback, **kwargs):
        super().__init__(**kwargs)
        self.producto = producto
        self.update_callback = update_callback
        self.title = f'Actualizar {producto["nombre"]}'
        self.size_hint = (0.8, 0.6)
        self.content = self.create_content()

    def create_content(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        layout.add_widget(Label(text=f'Unidades actuales: {self.producto["unidades"]}'))
        layout.add_widget(Label(text=f'Costo actual: ${self.producto["costo"]:,}'))
        
        self.unidades_input = TextInput(
            hint_text='Unidades adicionales',
            multiline=False,
            input_filter='int'
        )
        self.costo_input = TextInput(
            hint_text='Nuevo costo (opcional)',
            multiline=False,
            input_filter='int'
        )
        
        update_button = Button(
            text='Actualizar',
            size_hint_y=None,
            height='40dp',
            background_color=(0.2, 0.6, 1, 1)
        )
        update_button.bind(on_press=self.update_product)
        
        layout.add_widget(Label(text='Unidades a agregar:'))
        layout.add_widget(self.unidades_input)
        layout.add_widget(Label(text='Nuevo costo (dejar vacío para mantener):'))
        layout.add_widget(self.costo_input)
        layout.add_widget(update_button)
        
        return layout

    def update_product(self, instance):
        try:
            unidades_adicionales = int(self.unidades_input.text or '0')
            nuevo_costo = self.costo_input.text.strip()
            
            if nuevo_costo and not nuevo_costo.isdigit():
                self.show_error("El costo debe ser un número")
                return
                
            app = App.get_running_app()
            productos = app.db.get_all_products()
            
            for producto in productos:
                if producto['nombre'] == self.producto['nombre']:
                    producto['unidades'] += unidades_adicionales
                    if nuevo_costo:
                        producto['costo'] = int(nuevo_costo)
                    break
            
            app.db.update_product_units(self.producto['nombre'], producto['unidades'])
            self.update_callback()
            self.dismiss()
            
        except ValueError:
            self.show_error("Por favor ingrese valores válidos")

    def show_error(self, message):
        content = BoxLayout(orientation='vertical', padding=10)
        label = Label(
            text=message,
            text_size=(280, None),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        label.bind(texture_size=lambda *x: setattr(label, 'height', label.texture_size[1]))
        content.add_widget(label)
        
        popup = Popup(
            title='Error',
            content=content,
            size_hint=(None, None),
            size=(300, label.height + 100),
            auto_dismiss=True
        )
        popup.open()

class PrincipalScreen(BaseScreen):
    def __init__(self, **kwargs):
        super(PrincipalScreen, self).__init__(**kwargs)
        self.productos_rv = ProductosRV()
    
    def on_enter(self):
        app = App.get_running_app()
        print(f"Rol actual: {app.current_user_role}")
        
        self.productos_rv.load_products()
        self.ids.rv.data = self.productos_rv.data
        
        self.ids.admin_btn.opacity = 1 if app.current_user_role == 'admin' else 0
        self.ids.admin_btn.disabled = not (app.current_user_role == 'admin')
        self.ids.users_btn.opacity = 1 if app.current_user_role == 'admin' else 0
        self.ids.users_btn.disabled = not (app.current_user_role == 'admin')

    def generar_cotizacion(self):
        self.manager.current = 'cotizacion'

    def show_add_product_popup(self):
        def on_type_selected(tipo):
            if (tipo == 'nuevo'):
                popup = AddProductPopup(self.update_products)
                popup.open()
            else:
                self.show_product_selection()
        
        popup = SelectProductTypePopup(on_type_selected)
        popup.open()

    def show_product_selection(self):
        app = App.get_running_app()
        productos = app.db.get_all_products()
        
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        scroll_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        scroll_layout.bind(minimum_height=scroll_layout.setter('height'))
        
        for producto in productos:
            btn = Button(
                text=f"{producto['nombre']} - {producto['unidades']} unidades - ${producto['costo']:,}",
                size_hint_y=None,
                height='40dp'
            )
            btn.bind(on_press=lambda x, p=producto: self.show_update_popup(p))
            scroll_layout.add_widget(btn)
        
        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(scroll_layout)
        content.add_widget(scroll)
        
        popup = Popup(
            title='Seleccionar Producto',
            content=content,
            size_hint=(0.9, 0.9)
        )
        popup.open()

    def show_update_popup(self, producto):
        popup = UpdateProductPopup(producto, self.update_products)
        popup.open()
    
    def update_products(self):
        self.productos_rv.load_products()
        self.ids.rv.data = self.productos_rv.data

class ClientDataPopup(Popup):
    def __init__(self, generar_pdf_callback, **kwargs):
        super().__init__(**kwargs)
        self.generar_pdf_callback = generar_pdf_callback
        self.title = 'Datos del Cliente'
        self.size_hint = (0.9, 0.8)
        self.content = self.create_content()

    def create_content(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        self.tipo_doc = Spinner(
            text='Cédula de Ciudadanía',
            values=('Cédula de Ciudadanía', 'NIT', 'Cédula de Extranjería', 'Pasaporte'),
            size_hint_y=None,
            height='40dp'
        )
        
        self.num_documento = TextInput(hint_text='Número de Documento', multiline=False)
        self.nombres = TextInput(hint_text='Nombres', multiline=False)
        self.apellidos = TextInput(hint_text='Apellidos', multiline=False)
        self.telefono = TextInput(hint_text='Número Telefónico', multiline=False)
        self.email = TextInput(hint_text='Correo Electrónico', multiline=False)
        
        generar_btn = Button(
            text='Generar PDF',
            size_hint_y=None,
            height='50dp',
            background_color=(0.2, 0.6, 1, 1)
        )
        generar_btn.bind(on_press=self.submit)
        
        labels_inputs = [
            ('Tipo de Documento:', self.tipo_doc),
            ('Número de Documento:', self.num_documento),
            ('Nombres:', self.nombres),
            ('Apellidos:', self.apellidos),
            ('Teléfono:', self.telefono),
            ('Correo:', self.email)
        ]
        
        for label_text, input_widget in labels_inputs:
            layout.add_widget(Label(
                text=label_text,
                size_hint_y=None,
                height='30dp',
                halign='left'
            ))
            layout.add_widget(input_widget)
        
        layout.add_widget(Widget(size_hint_y=None, height='20dp'))
        layout.add_widget(generar_btn)
        
        return layout

    def submit(self, instance):
        if not all([self.num_documento.text, self.nombres.text, self.apellidos.text,
                   self.telefono.text, self.email.text]):
            self.show_error("Por favor complete todos los campos")
            return
            
        cliente_data = {
            'tipo_documento': self.tipo_doc.text,
            'numero_documento': self.num_documento.text,
            'nombres': self.nombres.text,
            'apellidos': self.apellidos.text,
            'telefono': self.telefono.text,
            'email': self.email.text
        }
        
        self.dismiss()
        self.generar_pdf_callback(cliente_data)

    def show_error(self, message):
        content = BoxLayout(orientation='vertical', padding=10)
        label = Label(
            text=message,
            text_size=(280, None),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        label.bind(texture_size=lambda *x: setattr(label, 'height', label.texture_size[1]))
        content.add_widget(label)
        
        popup = Popup(
            title='Error',
            content=content,
            size_hint=(None, None),
            size=(300, label.height + 100),
            auto_dismiss=True
        )
        popup.open()

class CotizacionScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.productos = []
        self.ambiente_count = 1
        self.total_productos = {}
        self.subtotal = 0
        self.iva = 0
        self.total_final = 0

    def on_enter(self):
        app = App.get_running_app()
        self.productos = app.db.get_all_products()
        self.crear_tabla()
        
    def crear_tabla(self):
        self.ids.tabla_container.clear_widgets()
        
        column_width = 250
        
        header = GridLayout(cols=len(self.productos) + 1, 
                          size_hint_y=None, 
                          height=60,
                          size_hint_x=None,
                          width=column_width * (len(self.productos) + 1))
        
        header.add_widget(Label(
            text='Ambiente',
            bold=True,
            color=[0,0,0,1],
            size_hint_x=None,
            width=column_width,
            text_size=(column_width-20, None),
            halign='center',
            valign='middle'
        ))
        
        for producto in self.productos:
            header.add_widget(Label(
                text=producto['nombre'],
                bold=True,
                color=[0,0,0,1],
                size_hint_x=None,
                width=column_width,
                text_size=(column_width-20, None),
                halign='center',
                valign='middle'
            ))
        
        self.ids.tabla_container.add_widget(header)
        
        for i in range(self.ambiente_count):
            self.agregar_fila_ambiente(i + 1)

    def agregar_fila_ambiente(self, num):
        column_width = 250
        
        fila = GridLayout(
            cols=len(self.productos) + 1,
            size_hint_y=None,
            height=60,
            size_hint_x=None,
            width=column_width * (len(self.productos) + 1)
        )
        
        fila.add_widget(Label(
            text=f'Ambiente {num}',
            color=[0,0,0,1],
            size_hint_x=None,
            width=column_width,
            text_size=(column_width-20, None),
            halign='center',
            valign='middle'
        ))
        
        for producto in self.productos:
            text_input = TextInput(
                multiline=False,
                input_filter='int',
                text='',
                hint_text='0',
                size_hint_x=None,
                width=column_width,
                height=40,
                halign='center',
                padding=(10, 10)
            )
            setattr(text_input, 'producto_ref', producto)
            text_input.bind(
                text=self.on_text_input_change,
                focus=self.on_focus
            )
            fila.add_widget(text_input)
        
        self.ids.tabla_container.add_widget(fila)

    def on_text_input_change(self, instance, value):
        if not value:
            self.actualizar_totales()
            return

        try:
            cantidad = int(value)
            producto = instance.producto_ref
            total_otros = self.calcular_total_otros(instance, producto)
            disponibles = producto['unidades'] - total_otros

            if cantidad > disponibles:
                mensaje = (
                    f"No hay suficientes unidades de {producto['nombre']}.\n"
                    f"Unidades totales: {producto['unidades']}\n"
                    f"En uso en otros ambientes: {total_otros}\n"
                    f"Disponibles: {disponibles}"
                )
                instance.text = str(disponibles)
                instance.readonly = True
                Clock.schedule_once(lambda dt: self.show_error(mensaje))
            
            self.actualizar_totales()
        except ValueError:
            instance.text = ''
            self.actualizar_totales()

    def on_focus(self, instance, value):
        if not value:
            instance.readonly = False

    def calcular_total_otros(self, current_input, producto):
        filas = [widget for widget in self.ids.tabla_container.children 
                if isinstance(widget, GridLayout)][:-1]
        
        return sum(
            int(other_input.text or '0')
            for other_fila in filas
            for other_input in [w for w in other_fila.children if isinstance(w, TextInput)]
            if hasattr(other_input, 'producto_ref') 
            and other_input.producto_ref['nombre'] == producto['nombre']
            and other_input != current_input
        )

    def actualizar_totales(self, instance=None, value=None):
        if not hasattr(self, '_actualizando'):
            self._actualizando = False
            
        if self._actualizando:
            return
            
        self._actualizando = True
        try:
            total = 0
            self.total_productos = {p['nombre']: 0 for p in self.productos}
            
            filas = [widget for widget in self.ids.tabla_container.children 
                    if isinstance(widget, GridLayout)][:-1]
            
            for fila in filas:
                inputs = [widget for widget in fila.children 
                         if isinstance(widget, TextInput)]
                inputs.reverse()
                
                for input_widget in inputs:
                    if not hasattr(input_widget, 'producto_ref'):
                        continue
                        
                    try:
                        producto = input_widget.producto_ref
                        valor_actual = input_widget.text.strip()
                        cantidad = int(valor_actual) if valor_actual else 0
                        
                        if cantidad < 0:
                            input_widget.text = ''
                            cantidad = 0
                            continue
                        
                        self.total_productos[producto['nombre']] += cantidad
                        subtotal = cantidad * int(producto['costo'])
                        total += subtotal
                        
                    except ValueError:
                        input_widget.text = ''
                        continue
            
            subtotal = total
            iva = subtotal * 0.19
            total_final = subtotal + iva
            
            self.ids.valor_plan.text = f"${subtotal:,.0f}"
            self.ids.valor_iva.text = f"${iva:,.0f}"
            self.ids.valor_total.text = f"${total_final:,.0f}"
            
        finally:
            self._actualizando = False

    def show_error(self, message):
        content = BoxLayout(orientation='vertical', padding=10)
        label = Label(
            text=message,
            text_size=(280, None),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        label.bind(texture_size=lambda *x: setattr(label, 'height', label.texture_size[1]))
        content.add_widget(label)
        
        popup = Popup(
            title='Control de Inventario',
            content=content,
            size_hint=(None, None),
            size=(300, label.height + 100),
            auto_dismiss=True
        )
        popup.open()

    def agregar_ambiente(self):
        self.ambiente_count += 1
        self.agregar_fila_ambiente(self.ambiente_count)
        self.actualizar_totales()

    def get_downloads_dir(self):
        if platform == 'android':
            from android.storage import primary_external_storage_path
            return join(primary_external_storage_path(), 'Download')
        else:
            return join(expanduser('~'), 'Downloads')

    def generar_pdf(self):
        self.manager.current = 'client_form'
    
    def generar_pdf_con_datos(self, cliente_data):
        try:
            app = App.get_running_app()
            valores = {
                'subtotal': float(self.ids.valor_plan.text.replace('$', '').replace(',', '')),
                'iva': float(self.ids.valor_iva.text.replace('$', '').replace(',', '')),
                'total': float(self.ids.valor_total.text.replace('$', '').replace(',', ''))
            }
            
            # Recolectar detalles por ambiente
            detalles_ambientes = {}
            filas = [widget for widget in self.ids.tabla_container.children 
                    if isinstance(widget, GridLayout)][:-1]
            filas.reverse()
            
            for num_ambiente, fila in enumerate(filas, 1):
                inputs = [widget for widget in fila.children if isinstance(widget, TextInput)]
                inputs.reverse()
                ambiente_detalles = {}
                
                for input_widget, producto in zip(inputs, self.productos):
                    cantidad = int(input_widget.text or '0')
                    if cantidad > 0:
                        ambiente_detalles[producto['id']] = {
                            'cantidad': cantidad,
                            'precio_unitario': float(producto['costo'])
                        }
                
                if ambiente_detalles:  # Solo agregar ambiente si tiene productos
                    detalles_ambientes[num_ambiente] = ambiente_detalles
            
            # Si no hay productos seleccionados, mostrar error
            if not detalles_ambientes:
                self.show_error("Debe seleccionar al menos un producto")
                return

            # Crear primero la cotización principal
            cotizacion_id = app.db.create_cotizacion(
                usuario_id=int(app.current_user_id),
                cliente_data=cliente_data,
                valores=valores
            )

            if not cotizacion_id:
                raise Exception("Error al crear la cotización")

            # Luego insertar los detalles de cada ambiente
            try:
                for ambiente_num, productos in detalles_ambientes.items():
                    for producto_id, detalle in productos.items():
                        app.db._execute_query("""
                            INSERT INTO cotizacion_detalles (
                                cotizacion_id, ambiente, producto_id, 
                                cantidad, precio_unitario
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            cotizacion_id, 
                            ambiente_num,
                            producto_id, 
                            detalle['cantidad'],
                            detalle['precio_unitario']
                        ))
            except Exception as e:
                # Si falla, eliminar la cotización principal
                app.db._execute_query("DELETE FROM cotizaciones WHERE id = %s", (cotizacion_id,))
                raise Exception(f"Error guardando detalles: {str(e)}")

            # Generar PDF
            downloads_dir = self.get_downloads_dir()
            os.makedirs(downloads_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = join(downloads_dir, f'cotizacion_{cotizacion_id}_{timestamp}.pdf')

            # Crear el documento PDF
            doc = SimpleDocTemplate(filename, pagesize=letter)
            elements = []

            # Título
            styles = getSampleStyleSheet()
            elements.append(Paragraph("Cotización de Productos", styles['Title']))
            elements.append(Spacer(1, 20))

            # Información del cliente
            elements.append(Paragraph("Información del Cliente", styles['Heading2']))
            cliente_info = [
                ['Tipo de Documento:', cliente_data['tipo_documento']],
                ['Número:', cliente_data['numero_documento']],
                ['Nombres:', cliente_data['nombres']],
                ['Apellidos:', cliente_data['apellidos']],
                ['Teléfono:', cliente_data['telefono']],
                ['Email:', cliente_data['email']]
            ]
            t = Table(cliente_info)
            t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t)
            elements.append(Spacer(1, 20))

            # Detalles por ambiente
            filas = [widget for widget in self.ids.tabla_container.children 
                    if isinstance(widget, GridLayout)][:-1]
            filas.reverse()

            for idx, fila in enumerate(filas, 1):
                elements.append(Paragraph(f"Ambiente {idx}", styles['Heading3']))
                
                data = [['Producto', 'Cantidad', 'Precio Unit.', 'Subtotal']]
                inputs = [w for w in fila.children if isinstance(w, TextInput)]
                inputs.reverse()
                
                ambiente_total = 0
                for input_widget, producto in zip(inputs, self.productos):
                    cantidad = int(input_widget.text or '0')
                    if cantidad > 0:
                        subtotal = cantidad * float(producto['costo'])
                        ambiente_total += subtotal
                        data.append([
                            producto['nombre'],
                            str(cantidad),
                            f"${producto['costo']:,.2f}",
                            f"${subtotal:,.2f}"
                        ])

                if len(data) > 1:  # Si hay productos en este ambiente
                    t = Table(data, colWidths=[200, 80, 100, 100])
                    t.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ]))
                    elements.append(t)
                    elements.append(Paragraph(f"Total Ambiente {idx}: ${ambiente_total:,.2f}", styles['Normal']))
                    elements.append(Spacer(1, 10))

            # Totales
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"Subtotal: ${valores['subtotal']:,.2f}", styles['Heading4']))
            elements.append(Paragraph(f"IVA (19%): ${valores['iva']:,.2f}", styles['Heading4']))
            elements.append(Paragraph(f"Total: ${valores['total']:,.2f}", styles['Heading2']))

            # Generar el PDF
            doc.build(elements)
            
            # Actualizar inventario
            self.actualizar_inventario()
            
            # Mostrar modal de éxito
            content = BoxLayout(orientation='vertical', spacing=10, padding=20)
            content.add_widget(Label(
                text=f"¡Cotización generada exitosamente!\n\n"
                     f"ID de Cotización: {cotizacion_id}\n\n"
                     f"PDF guardado en:\n{filename}",
                halign='center',
                text_size=(400, None),
                size_hint_y=None,
                height=200
            ))
            
            ok_button = Button(
                text="Aceptar",
                size_hint=(None, None),
                size=(150, 50),
                pos_hint={'center_x': 0.5}
            )
            
            content.add_widget(ok_button)
            
            popup = Popup(
                title='PDF Generado',
                content=content,
                size_hint=(None, None),
                size=(500, 300),
                auto_dismiss=False
            )
            
            ok_button.bind(on_press=popup.dismiss)
            popup.open()

        except Exception as e:
            self.show_error(f"Error al generar la cotización: {str(e)}")

    def actualizar_inventario(self):
        app = App.get_running_app()
        for producto in self.productos:
            cantidad_usada = self.total_productos[producto['nombre']]
            if cantidad_usada > 0:
                nuevas_unidades = int(producto['unidades']) - cantidad_usada
                try:
                    app.db.update_product_units(producto['nombre'], nuevas_unidades)
                except Exception as e:
                    print(f"Error actualizando {producto['nombre']}: {str(e)}")
                    continue
        
        self.manager.get_screen('principal').update_products()

    def show_success(self, message):
        content = BoxLayout(orientation='vertical', padding=10)
        label = Label(
            text=message,
            text_size=(280, None),
            size_hint_y=None,
            halign='center',
            valign='middle'
        )
        label.bind(texture_size=lambda *x: setattr(label, 'height', label.texture_size[1]))
        content.add_widget(label)
        
        popup = Popup(
            title='Éxito',
            content=content,
            size_hint=(None, None),
            size=(300, label.height + 100),
            auto_dismiss=True
        )
        popup.open()

class UsersScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user_id = None
        
    def on_enter(self):
        self.load_users()
        app = App.get_running_app()
        if app.current_user_role != 'admin':
            self.disable_admin_actions()
    
    def disable_admin_actions(self):
        container = self.ids.users_container
        for widget in container.walk():
            if isinstance(widget, Button):
                widget.disabled = True
                widget.opacity = 0
    
    def load_users(self):
        app = App.get_running_app()
        users = app.db.get_all_users()
        container = self.ids.users_container
        container.clear_widgets()
        
        for user_id, user_data in users:
            container.add_widget(Label(
                text=str(user_id),
                color=(0,0,0,1),
                size_hint_y=None,
                height='40dp'
            ))
            container.add_widget(Label(
                text=str(user_data['username']),
                color=(0,0,0,1),
                size_hint_y=None,
                height='40dp'
            ))
            container.add_widget(Label(
                text=str(user_data['role']),
                color=(0,0,0,1),
                size_hint_y=None,
                height='40dp'
            ))
            actions = BoxLayout(size_hint_y=None, height='40dp', spacing='10dp')
            if user_id != 'admin':
                edit_btn = MDIconButton(
                    icon="pencil",
                    theme_text_color="Custom",
                    text_color=(0.2, 0.6, 1, 1),
                    size_hint=(None, None),
                    size=('40dp', '40dp')
                )
                edit_btn.bind(on_press=lambda x, uid=user_id: self.show_edit_popup(uid))
                
                delete_btn = MDIconButton(
                    icon="delete",
                    theme_text_color="Custom",
                    text_color=(1, 0.2, 0.2, 1),
                    size_hint=(None, None),
                    size=('40dp', '40dp')
                )
                delete_btn.bind(on_press=lambda x, uid=user_id: self.delete_user(uid))
                
                actions.add_widget(edit_btn)
                actions.add_widget(delete_btn)
            container.add_widget(actions)

    def show_add_user_popup(self):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)

    def show_edit_popup(self, user_id):
        app = App.get_running_app()
        user_data = app.db.get_user_data(user_id)
        if not user_data:
            return

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        username_input = TextInput(
            text=user_data['username'],
            hint_text='Nombre de Usuario',
            multiline=False,
            size_hint_y=None,
            height='40dp'
        )
        
        role_spinner = Spinner(
            text=user_data['role'],
            values=('admin', 'client'),
            size_hint_y=None,
            height='40dp'
        )
        
        update_btn = Button(
            text='Actualizar',
            size_hint_y=None,
            height='40dp',
            background_color=(0.2, 0.6, 1, 1)
        )
        
        content.add_widget(Label(text='Nombre de Usuario:'))
        content.add_widget(username_input)
        content.add_widget(Label(text='Rol:'))
        content.add_widget(role_spinner)
        content.add_widget(update_btn)

        popup = Popup(
            title=f'Editar Usuario: {user_id}',
            content=content,
            size_hint=(0.8, 0.8)
        )

        def update(instance):
            app.db.update_user(
                user_id,
                username=username_input.text,
                role=role_spinner.text
            )
            self.load_users()
            popup.dismiss()

        update_btn.bind(on_press=update)
        popup.open()

    def delete_user(self, user_id):
        app = App.get_running_app()
        if app.db.delete_user(user_id):
            self.load_users()

class UsuarioRow(BoxLayout):
    pass

class NavDrawer(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = ('20dp', '0dp', '20dp', '20dp')
        self.spacing = '15dp'
        self.size_hint = (None, 1)
        self.width = Window.width * 0.8
        
        with self.canvas.before:
            Color(0.118, 0.227, 0.373, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        header = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height='50dp'
        )
        
        header.add_widget(Label(
            text='Menú',
            color=(1, 1, 1, 1),
            bold=True,
            font_size='24sp',
            size_hint_x=0.8,
            halign='left'
        ))
        
        close_btn = MDIconButton(
            icon="close",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            size_hint_x=0.2,
            pos_hint={"center_y": .5}
        )
        close_btn.bind(on_press=lambda x: App.get_running_app().close_nav_drawer())
        header.add_widget(close_btn)
        self.add_widget(header)

        buttons_container = BoxLayout(
            orientation='vertical',
            spacing='15dp',
            padding=('0dp', '20dp', '0dp', '0dp'),
            size_hint_y=None,
            height='200dp'
        )

        buttons = []
        
        principal_btn = Button(
            text='Principal',
            size_hint_y=None,
            height='50dp',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            border=(2, 2, 2, 2)
        )
        principal_btn.bind(on_press(lambda x: self.navigate_to('principal')))
        buttons.append(principal_btn)

        cotizacion_btn = Button(
            text='Cotización',
            size_hint_y=None,
            height='50dp',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            border=(2, 2, 2, 2)
        )
        cotizacion_btn.bind(on_press(lambda x: self.navigate_to('cotizacion')))
        buttons.append(cotizacion_btn)

        app = App.get_running_app()
        if app.current_user_role == 'admin':
            users_btn = Button(
                text='Usuarios',
                size_hint_y=None,
                height='50dp',
                background_color=(0, 0, 0, 0),
                color=(1, 1, 1, 1),
                border=(2, 2, 2, 2)
            )
            users_btn.bind(on_press(lambda x: self.navigate_to('users')))
            buttons.append(users_btn)

        logout_btn = Button(
            text='Cerrar Sesión',
            size_hint_y=None,
            height='50dp',
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1),
            border=(2, 2, 2, 2)
        )
        logout_btn.bind(on_press(lambda x: self.navigate_to('login')))
        buttons.append(logout_btn)

        for btn in buttons:
            with btn.canvas.before:
                Color(1, 1, 1, 1)
                Line(rectangle=(btn.x, btn.y, btn.width, btn.height), width=1.5)
            buttons_container.add_widget(btn)

        self.add_widget(buttons_container)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def navigate_to(self, screen_name):
        app = App.get_running_app()
        app.root.current = screen_name
        app.root.close_nav_drawer()

class NavigationDrawer(ModalView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.8, 1)
        self.pos_hint = {'right': 0.8, 'top': 1}
        self.background_color = (0, 0, 0.545, 0.5)
        self.nav_drawer = NavDrawer()
        self.add_widget(self.nav_drawer)
        self.bind(on_touch_down=self.check_touch_close)

    def check_touch_close(self, instance, touch):
        if not self.nav_drawer.collide_point(*touch.pos):
            anim = Animation(
                background_color=(0, 0, 0.545, 0),
                duration=0.2
            )
            anim.bind(on_complete=lambda *args: self.dismiss())
            anim.start(self)
            return True
        return super().on_touch_down(touch)

    def open(self):
        if not self.parent:
            Window.add_widget(self)
        Animation(background_color=(0, 0, 0.545, 0.5), duration=0.2).start(self)

class NavBar(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class ClientFormScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.productos = []
        self.total_productos = {}
        
    def on_enter(self):
        cotizacion_screen = self.manager.get_screen('cotizacion')
        self.productos = cotizacion_screen.productos
        self.total_productos = cotizacion_screen.total_productos
        self.subtotal = float(cotizacion_screen.ids.valor_plan.text.replace('$', '').replace(',', ''))
        self.iva = float(cotizacion_screen.ids.valor_iva.text.replace('$', '').replace(',', ''))
        self.total = float(cotizacion_screen.ids.valor_total.text.replace('$', '').replace(',', ''))

    def validate_fields(self):
        num_documento = self.ids.num_documento.text.strip()
        if not num_documento.isdigit():
            self.show_error("El número de documento debe contener solo números")
            return False

        if len(num_documento) < 8 or len(num_documento) > 12:
            self.show_error("El número de documento debe tener entre 8 y 12 dígitos")
            self.ids.num_documento.text = num_documento[:12]
            return False

        if not all(c.isalpha() or c.isspace() for c in self.ids.nombres.text):
            self.show_error("Los nombres solo deben contener letras")
            return False

        if not all(c.isalpha() or c.isspace() for c in self.ids.apellidos.text):
            self.show_error("Los apellidos solo deben contener letras")
            return False

        if not self.ids.telefono.text.isdigit():
            self.show_error("El teléfono debe contener solo números")
            return False

        if len(self.ids.telefono.text) != 10:
            self.show_error("El teléfono debe tener 10 dígitos")
            return False

        if '@' not in self.ids.email.text:
            self.show_error("El email debe contener @")
            return False

        if not self.validate_email_format(self.ids.email.text):
            self.show_error("Formato de email inválido")
            return False

        return True

    def validate_email_format(self, email):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def submit(self):
        if not self.validate_fields():
            return

        if not all([self.ids.num_documento.text, self.ids.nombres.text, 
                    self.ids.apellidos.text, self.ids.telefono.text, 
                    self.ids.email.text]):
            self.show_error("Por favor complete todos los campos")
            return
            
        cliente_data = {
            'tipo_documento': self.ids.tipo_doc.text,
            'numero_documento': self.ids.num_documento.text,
            'nombres': self.ids.nombres.text,
            'apellidos': self.ids.apellidos.text,
            'telefono': self.ids.telefono.text,
            'email': self.ids.email.text
        }
        
        cotizacion_screen = self.manager.get_screen('cotizacion')
        cotizacion_screen.generar_pdf_con_datos(cliente_data)
        self.manager.current = 'cotizacion'

class MainApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user_id = None
        self.current_user_role = None
        self.db = Database()
        self.db.initialize_database()

    def validate_user(self, id_number, password):
        return self.db.validate_user(id_number, password)

    def get_user_role(self, id_number):
        return self.db.get_user_role(id_number)

    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(PrincipalScreen(name='principal'))
        sm.add_widget(CotizacionScreen(name='cotizacion'))
        sm.add_widget(UsersScreen(name='users'))
        sm.add_widget(ClientFormScreen(name='client_form'))
        
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        
        return sm

if __name__ == '__main__':
    MainApp().run()

