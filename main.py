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
from functools import partial
from user_store import UserStore
from product_store import ProductStore
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.platypus.flowables import HRFlowable  # Añadir esta importación
from datetime import datetime
import os
from kivy.utils import platform
from os.path import expanduser, join
from kivy.uix.modalview import ModalView
from kivy.core.window import Window  # Add this import
from kivy.graphics import Color, Rectangle, Line  # Add this import
from kivymd.app import MDApp
from kivymd.uix.button import MDIconButton
from kivy.uix.spinner import Spinner  # Añadir esta importación
import sqlite3
import traceback

class LoadingScreen(Screen):
    logo = ObjectProperty(None)
    
    def on_enter(self):
        anim = Animation(opacity=1, duration=2)
        anim.bind(on_complete=self.start_exit_animation)
        anim.start(self.logo)
    
    def start_exit_animation(self, *args):
        Clock.schedule_once(self.begin_exit, 1)
    
    def begin_exit(self, dt):
        anim = Animation(opacity=0, duration=2)
        anim.bind(on_complete=self.switch_screen)
        anim.start(self.logo)
    
    def switch_screen(self, *args):
        self.manager.current = 'login'

class LoginScreen(Screen):
    def validate_login(self, id_number, password):
        if not id_number or not password:
            self.show_error("Por favor complete todos los campos")
            return False
        
        app = App.get_running_app()
        if app.validate_user(id_number, password):  # Usando el método de MainApp
            return True
        
        self.show_error("Identificación o contraseña incorrecta")
        return False

    def on_login_press(self):
        id_number = self.ids.id_input.text
        password = self.ids.password_input.text
        
        if self.validate_login(id_number, password):
            app = App.get_running_app()
            app.current_user_id = id_number  # Guardar ID del usuario actual
            app.current_user_role = app.get_user_role(id_number)  # Usando el método de MainApp
            print(f"Usuario logueado con rol: {app.current_user_role}")  # Debug line
            self.show_success("Inicio de sesión exitoso")
            self.manager.current = 'principal'

    def on_create_account_press(self):
        self.manager.current = 'register'

    def show_error(self, message):
        popup = Popup(title='Error',
                     content=Label(text=message),
                     size_hint=(None, None), size=(300, 200))
        popup.open()

    def show_success(self, message):
        popup = Popup(title='Éxito',
                     content=Label(text=message),
                     size_hint=(None, None), size=(300, 200))
        popup.open()

class RegisterScreen(Screen):
    def validate_registration(self, username, id_number, password, confirm_password):
        if not all([username, id_number, password, confirm_password]):
            self.show_error("Por favor complete todos los campos")
            return False
        
        if not id_number.isdigit():
            self.show_error("El número de identificación debe contener solo números")
            return False

        if len(password) < 6:
            self.show_error("La contraseña debe tener al menos 6 caracteres")
            return False

        if password != confirm_password:
            self.show_error("Las contraseñas no coinciden")
            return False

        return True

    def on_register_press(self):
        username = self.ids.reg_username.text
        id_number = self.ids.reg_id_number.text
        password = self.ids.reg_password.text
        confirm_password = self.ids.reg_confirm_password.text

        if self.validate_registration(username, id_number, password, confirm_password):
            app = App.get_running_app()
            # Por defecto, los nuevos usuarios son clientes
            app.user_store.add_user(id_number, username, password, 'client')
            self.show_success("Registro exitoso")
            self.manager.current = 'login'

    def show_error(self, message):
        popup = Popup(title='Error',
                     content=Label(text=message),
                     size_hint=(None, None), size=(300, 200))
        popup.open()

    def show_success(self, message):
        popup = Popup(title='Éxito',
                     content=Label(text=message),
                     size_hint=(None, None), size=(300, 200))
        popup.open()

class ProductosRV(RecycleView):
    data = ListProperty([])
    
    def __init__(self, **kwargs):
        super(ProductosRV, self).__init__(**kwargs)
        self.load_products()
    
    def load_products(self):
        app = App.get_running_app()
        productos = app.product_store.get_all_products()  # Usando product_store en lugar de database
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
        app.product_store.add_product(nombre, unidades, costo)
        self.update_callback()
        self.dismiss()

    def show_error(self, message):
        popup = Popup(
            title='Error',
            content=Label(text=message),
            size_hint=(None, None),
            size=(300, 200)
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
        
        # Mostrar datos actuales
        layout.add_widget(Label(text=f'Unidades actuales: {self.producto["unidades"]}'))
        layout.add_widget(Label(text=f'Costo actual: ${self.producto["costo"]:,}'))
        
        # Inputs para nuevos valores
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
            
            if nuevo_costo and not nuevo_costo.isdigit():  # Corregido && por and
                self.show_error("El costo debe ser un número")
                return
                
            app = App.get_running_app()
            productos = app.product_store.get_all_products()
            
            for producto in productos:
                if producto['nombre'] == self.producto['nombre']:
                    producto['unidades'] += unidades_adicionales
                    if nuevo_costo:
                        producto['costo'] = int(nuevo_costo)
                    break
            
            app.product_store._save_products(productos)
            self.update_callback()
            self.dismiss()
            
        except ValueError:
            self.show_error("Por favor ingrese valores válidos")

    def show_error(self, message):
        popup = Popup(
            title='Error',
            content=Label(text=message),
            size_hint=(None, None),
            size=(300, 200)
        )
        popup.open()

class PrincipalScreen(Screen):
    def __init__(self, **kwargs):
        super(PrincipalScreen, self).__init__(**kwargs)
        self.productos_rv = ProductosRV()
    
    def on_enter(self):
        app = App.get_running_app()
        print(f"Rol actual: {app.current_user_role}")  # Debug line
        
        # Actualizar productos
        self.productos_rv.load_products()
        self.ids.rv.data = self.productos_rv.data
        
        # Actualizar visibilidad de botones
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
        productos = app.product_store.get_all_products()
        
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

class CotizacionScreen(Screen):
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
        self.productos = app.product_store.get_all_products()
        self.crear_tabla()
        
    def crear_tabla(self):
        self.ids.tabla_container.clear_widgets()
        
        # Aumentar el ancho de las columnas
        column_width = 250  # Aumentado de 200 a 250
        
        header = GridLayout(cols=len(self.productos) + 1, 
                          size_hint_y=None, 
                          height=60,  # Aumentado de 40 a 60
                          size_hint_x=None,
                          width=column_width * (len(self.productos) + 1))
        
        header.add_widget(Label(
            text='Ambiente',
            bold=True,
            color=[0,0,0,1],
            size_hint_x=None,
            width=column_width,
            text_size=(column_width-20, None),  # Margen para el texto
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
                text_size=(column_width-20, None),  # Margen para el texto
                halign='center',
                valign='middle'
            ))
        
        self.ids.tabla_container.add_widget(header)
        
        for i in range(self.ambiente_count):
            self.agregar_fila_ambiente(i + 1)

    def agregar_fila_ambiente(self, num):
        column_width = 250  # Mismo ancho que en crear_tabla
        
        fila = GridLayout(
            cols=len(self.productos) + 1,
            size_hint_y=None,
            height=60,  # Aumentado para mejor legibilidad
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
                text='0',
                size_hint_x=None,
                width=column_width,
                height=40,
                halign='center',
                padding=(10, 10)  # Añadir padding al texto
            )
            text_input.bind(text=self.actualizar_totales)
            fila.add_widget(text_input)
        
        self.ids.tabla_container.add_widget(fila)

    def actualizar_totales(self, instance=None, value=None):
        total = 0
        self.total_productos = {p['nombre']: 0 for p in self.productos}
        app = App.get_running_app()
        
        # Obtener todas las filas excepto el encabezado
        filas = [widget for widget in self.ids.tabla_container.children 
                if isinstance(widget, GridLayout)][:-1]
        
        # Primero calcular el total actual por producto en todos los ambientes
        totales_por_producto = {p['nombre']: 0 for p in self.productos}
        for fila in filas:
            inputs = [widget for widget in fila.children 
                     if isinstance(widget, TextInput)]
            inputs.reverse()
            
            for input_widget, producto in zip(inputs, self.productos):
                try:
                    # Limpiar ceros a la izquierda
                    text_value = input_widget.text.lstrip('0')
                    cantidad = int(text_value) if text_value else 0
                    if text_value != input_widget.text:
                        input_widget.text = str(cantidad) if cantidad > 0 else '0'
                    
                    if cantidad < 0:
                        cantidad = 0
                        input_widget.text = '0'
                    totales_por_producto[producto['nombre']] += cantidad
                except ValueError:
                    continue

        # Ahora procesar cada input verificando los totales
        for fila in filas:
            inputs = [widget for widget in fila.children 
                     if isinstance(widget, TextInput)]
            inputs.reverse()
            
            for input_widget, producto in zip(inputs, self.productos):
                try:
                    cantidad_actual = int(input_widget.text or '0')
                    if cantidad_actual < 0:
                        input_widget.text = '0'
                        cantidad_actual = 0
                    
                    # Calcular el total sin contar este input
                    total_otros = totales_por_producto[producto['nombre']] - cantidad_actual
                    maximo_disponible = producto['unidades'] - total_otros
                    
                    # Verificar y ajustar si es necesario
                    if cantidad_actual > maximo_disponible:
                        input_widget.text = str(maximo_disponible)  # Establecer el máximo disponible
                        cantidad_actual = maximo_disponible
                        self.show_error(f"Se ha ajustado automáticamente la cantidad de {producto['nombre']} al máximo disponible: {maximo_disponible}")
                    
                    costo = int(producto['costo'])
                    subtotal = cantidad_actual * costo
                    self.total_productos[producto['nombre']] += cantidad_actual
                    total += subtotal
                except ValueError:
                    continue
        
        # Actualizar labels
        subtotal = total
        iva = subtotal * 0.19
        total_final = subtotal + iva
        
        self.ids.valor_plan.text = f"${subtotal:,.0f}"
        self.ids.valor_iva.text = f"${iva:,.0f}"
        self.ids.valor_total.text = f"${total_final:,.0f}"

    def show_error(self, message):
        popup = Popup(
            title='Error',
            content=Label(text=message),
            size_hint=(None, None),
            size=(400, 200)
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
        # Obtener directorio de descargas
        downloads_dir = self.get_downloads_dir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = join(downloads_dir, f'cotizacion_{timestamp}.pdf')

        # Configurar el documento
        doc = SimpleDocTemplate(filename, pagesize=letter,
                              rightMargin=50, leftMargin=50,
                              topMargin=50, bottomMargin=50)
        elements = []

        # Estilos personalizados
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            textColor=colors.HexColor('#1E3A5F'),
            spaceAfter=40,
            fontSize=24,
            alignment=1  # Centrado
        )

        ambiente_style = ParagraphStyle(
            'AmbienteStyle',
            parent=styles['Heading2'],
            textColor=colors.HexColor('#2E4D7B'),
            spaceAfter=15,
            fontSize=14,
            spaceBefore=20
        )

        total_style = ParagraphStyle(
            'TotalStyle',
            parent=styles['Normal'],
            textColor=colors.HexColor('#1E3A5F'),
            fontSize=12,
            alignment=2  # Derecha
        )

        # Título y fecha
        elements.append(Paragraph("Cotización de Productos", title_style))
        elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ambiente_style))
        elements.append(Spacer(1, 20))

        # Obtener datos por ambiente y ordenarlos de forma ascendente
        filas = [widget for widget in self.ids.tabla_container.children 
                if isinstance(widget, GridLayout)][:-1]
        filas.reverse()  # Invertir el orden para que sea ascendente
        
        # Para cada ambiente
        for fila in filas:
            ambiente = fila.children[-1].text
            inputs = [widget for widget in fila.children if isinstance(widget, TextInput)]
            inputs.reverse()
            
            # Solo procesar ambientes que tengan productos seleccionados
            productos_ambiente = []
            subtotal_ambiente = 0
            
            for input_widget, producto in zip(inputs, self.productos):
                cantidad = int(input_widget.text or '0')
                if cantidad > 0:
                    subtotal_producto = cantidad * int(producto['costo'])
                    productos_ambiente.append([
                        producto['nombre'],
                        str(cantidad),
                        f"${int(producto['costo']):,}",
                        f"${subtotal_producto:,}"
                    ])
                    subtotal_ambiente += subtotal_producto
            
            if productos_ambiente:
                # Título del ambiente
                elements.append(Paragraph(f"Resumen {ambiente}", ambiente_style))
                
                # Tabla del ambiente
                data = [['Producto', 'Cantidad', 'Valor Unit.', 'Subtotal']] + productos_ambiente
                table = Table(data, colWidths=[200, 80, 100, 100])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4D7B')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2E4D7B')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F8FB')),
                ]))
                elements.append(table)
                elements.append(Paragraph(f"Subtotal {ambiente}: ${subtotal_ambiente:,}", total_style))
                elements.append(Spacer(1, 10))

        # Línea divisoria
        elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#2E4D7B'),
            spaceBefore=20,
            spaceAfter=20
        ))

        # Totales finales
        subtotal = float(self.ids.valor_plan.text.replace('$', '').replace(',', ''))
        iva = float(self.ids.valor_iva.text.replace('$', '').replace(',', ''))
        total = float(self.ids.valor_total.text.replace('$', '').replace(',', ''))

        elements.extend([
            Paragraph(f"Valor Plan Personalizado: ${subtotal:,.0f}", total_style),
            Paragraph(f"IVA (19%): ${iva:,.0f}", total_style),
            Paragraph(f"<b>Total: ${total:,.0f}</b>", total_style)
        ])

        # Generar PDF
        doc.build(elements)
        self.actualizar_inventario()
        self.show_success(f"PDF generado exitosamente en:\n{filename}")

    def actualizar_inventario(self):
        app = App.get_running_app()
        for producto in self.productos:
            cantidad_usada = self.total_productos[producto['nombre']]
            if cantidad_usada > 0:
                nuevas_unidades = int(producto['unidades']) - cantidad_usada
                app.product_store.update_product_units(producto['nombre'], nuevas_unidades)
        
        # Actualizar la vista de productos
        self.manager.get_screen('principal').update_products()

    def show_success(self, message):
        popup = Popup(
            title='Éxito',
            content=Label(text=message),
            size_hint=(None, None),
            size=(400, 200)
        )
        popup.open()

class UsersScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user_id = None
        
    def on_enter(self):
        self.load_users()
        app = App.get_running_app()
        # Deshabilitar botones si no es admin
        if app.current_user_role != 'admin':
            self.disable_admin_actions()
    
    def disable_admin_actions(self):
        # Deshabilitar los botones de acción en la lista de usuarios
        container = self.ids.users_container
        for widget in container.walk():
            if isinstance(widget, Button):
                widget.disabled = True
                widget.opacity = 0
    
    def load_users(self):
        app = App.get_running_app()
        users = app.user_store.get_all_users()
        container = self.ids.users_container
        container.clear_widgets()
        
        for user_id, user_data in users:
            # ID
            container.add_widget(Label(
                text=user_id,
                color=(0,0,0,1),
                size_hint_y=None,
                height='40dp'
            ))
            # Username
            container.add_widget(Label(
                text=user_data['username'],
                color=(0,0,0,1),
                size_hint_y=None,
                height='40dp'
            ))
            # Role
            container.add_widget(Label(
                text=user_data['role'],
                color=(0,0,0,1),
                size_hint_y=None,
                height='40dp'
            ))
            # Actions
            actions = BoxLayout(size_hint_y=None, height='40dp', spacing='10dp')
            if user_id != 'admin':  # No permitir modificar al admin
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
        # ... implementar popup para agregar usuario ...

    def show_edit_popup(self, user_id):
        app = App.get_running_app()
        user_data = app.user_store.get_user_data(user_id)
        if not user_data:
            return

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Campos de edición
        username_input = TextInput(
            text=user_data['username'],
            hint_text='Nombre de Usuario',
            multiline=False,
            size_hint_y=None,
            height='40dp'
        )
        
        # Spinner para selección de rol
        role_spinner = Spinner(
            text=user_data['role'],
            values=('admin', 'client'),
            size_hint_y=None,
            height='40dp'
        )
        
        # Botón de actualizar
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
            app.user_store.update_user(
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
        if app.user_store.delete_user(user_id):
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

        # Header
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

        # Contenedor de botones
        buttons_container = BoxLayout(
            orientation='vertical',
            spacing='15dp',
            padding=('0dp', '20dp', '0dp', '0dp'),
            size_hint_y=None,
            height='200dp'
        )

        # Lista de botones
        buttons = []
        
        # Botón Principal
        principal_btn = Button(
            text='Principal',
            size_hint_y=None,
            height='50dp',
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
            border=(2, 2, 2, 2)
        )
        principal_btn.bind(on_press=lambda x: self.navigate_to('principal'))
        buttons.append(principal_btn)

        # Botón Cotización
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

        # Botón Usuarios (solo para admin)
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

        # Botón Cerrar Sesión
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

        # Añadir botones al contenedor
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
        self.pos_hint = {'right': 0.8, 'top': 1}  # Posicionamiento en la parte superior
        # Fondo azul translúcido para el overlay
        self.background_color = (0, 0, 0.545, 0.5)  # rgba(0, 0, 139, 0.5)
        self.nav_drawer = NavDrawer()
        self.add_widget(self.nav_drawer)
        self.bind(on_touch_down=self.check_touch_close)

    def check_touch_close(self, instance, touch):
        # Cerrar solo si el toque es fuera del drawer
        if not self.nav_drawer.collide_point(*touch.pos):
            anim = Animation(
                background_color=(0, 0, 0.545, 0),
                duration=0.2
            )
            anim.bind(on_complete=lambda *args: self.dismiss())  # Corregido
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

class MainApp(MDApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_user_id = None
        self.current_user_role = None
        self.user_store = UserStore()
        self.product_store = ProductStore()

    def validate_user(self, id_number, password):
        return self.user_store.validate_user(id_number, password)

    def get_user_role(self, id_number):
        return self.user_store.get_user_role(id_number)

    def build(self):
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(PrincipalScreen(name='principal'))
        sm.add_widget(CotizacionScreen(name='cotizacion'))
        sm.add_widget(UsersScreen(name='users'))
        
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        
        return sm

if __name__ == '__main__':
    MainApp().run()

