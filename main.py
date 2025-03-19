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
from datetime import datetime
import os
from kivy.utils import platform
from os.path import expanduser, join

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
        if app.user_store.validate_user(id_number, password):
            return True
        
        self.show_error("Identificación o contraseña incorrecta")
        return False

    def on_login_press(self):
        id_number = self.ids.id_input.text
        password = self.ids.password_input.text
        
        if self.validate_login(id_number, password):
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
            app.user_store.add_user(id_number, username, password)
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
        productos = app.product_store.get_all_products()
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

class PrincipalScreen(Screen):
    def __init__(self, **kwargs):
        super(PrincipalScreen, self).__init__(**kwargs)
        self.productos_rv = ProductosRV()
    
    def on_enter(self):
        # Actualizar productos al entrar a la pantalla
        self.productos_rv.load_products()
        self.ids.rv.data = self.productos_rv.data

    def generar_cotizacion(self):
        self.manager.current = 'cotizacion'

    def show_add_product_popup(self):
        popup = AddProductPopup(self.update_products)
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
        
        # Crear encabezados con ancho fijo
        header = GridLayout(cols=len(self.productos) + 1, 
                          size_hint_y=None, 
                          height=40,
                          size_hint_x=None,
                          width=200 * (len(self.productos) + 1))  # 200dp por columna
        
        header.add_widget(Label(text='Ambiente', 
                              bold=True, 
                              color=[0,0,0,1],
                              size_hint_x=None,
                              width=200))
        
        for producto in self.productos:
            header.add_widget(Label(text=producto['nombre'],
                                  bold=True,
                                  color=[0,0,0,1],
                                  size_hint_x=None,
                                  width=200))
        
        self.ids.tabla_container.add_widget(header)
        
        for i in range(self.ambiente_count):
            self.agregar_fila_ambiente(i + 1)

    def agregar_fila_ambiente(self, num):
        fila = GridLayout(cols=len(self.productos) + 1,
                         size_hint_y=None,
                         height=40,
                         size_hint_x=None,
                         width=200 * (len(self.productos) + 1))  # Mismo ancho que el header
        
        fila.add_widget(Label(text=f'Ambiente {num}',
                            color=[0,0,0,1],
                            size_hint_x=None,
                            width=200))
        
        for producto in self.productos:
            text_input = TextInput(
                multiline=False,
                input_filter='int',
                text='0',
                size_hint_x=None,
                width=200,
                height=40,
                halign='center'
            )
            text_input.bind(text=self.actualizar_totales)
            fila.add_widget(text_input)
        
        self.ids.tabla_container.add_widget(fila)

    def actualizar_totales(self, instance=None, value=None):
        total = 0
        self.total_productos = {p['nombre']: 0 for p in self.productos}
        
        # Obtener todas las filas excepto el encabezado
        filas = [widget for widget in self.ids.tabla_container.children 
                if isinstance(widget, GridLayout)][:-1]
        
        for fila in filas:
            inputs = [widget for widget in fila.children 
                     if isinstance(widget, TextInput)]
            inputs.reverse()
            
            for input_widget, producto in zip(inputs, self.productos):
                try:
                    cantidad = int(input_widget.text or '0')
                    costo = int(producto['costo'])
                    subtotal = cantidad * costo
                    self.total_productos[producto['nombre']] += cantidad
                    total += subtotal
                except ValueError:
                    continue
        
        # Calcular totales
        subtotal = total
        iva = subtotal * 0.19
        total_final = subtotal + iva
        
        # Actualizar labels con formato de moneda
        self.ids.valor_plan.text = f"${subtotal:,.0f}"
        self.ids.valor_iva.text = f"${iva:,.0f}"
        self.ids.valor_total.text = f"${total_final:,.0f}"

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
                              rightMargin=30, leftMargin=30,
                              topMargin=30, bottomMargin=30)
        elements = []

        # Estilos personalizados
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            textColor=colors.HexColor('#1E3A5F'),
            spaceAfter=30,
            fontSize=24,
            alignment=1  # Centrado
        )

        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            textColor=colors.HexColor('#2E4D7B'),
            spaceAfter=20,
            fontSize=16
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
        elements.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", subtitle_style))
        
        # Datos de la tabla con formato mejorado
        table_data = [['Ambiente'] + [p['nombre'] for p in self.productos]]
        
        filas = [widget for widget in self.ids.tabla_container.children 
                if isinstance(widget, GridLayout)][:-1]
        
        totales_por_producto = {p['nombre']: {'cantidad': 0, 'total': 0} for p in self.productos}
        
        for fila in filas:
            ambiente = fila.children[-1].text
            inputs = [widget for widget in fila.children if isinstance(widget, TextInput)]
            inputs.reverse()
            row_data = [ambiente]
            
            for input_widget, producto in zip(inputs, self.productos):
                cantidad = int(input_widget.text or '0')
                row_data.append(str(cantidad))
                
                if cantidad > 0:
                    totales_por_producto[producto['nombre']]['cantidad'] += cantidad
                    totales_por_producto[producto['nombre']]['total'] += cantidad * producto['costo']
            
            table_data.append(row_data)

        # Resumen de productos
        elements.append(Paragraph("Resumen por Producto:", subtitle_style))
        resumen_data = [['Producto', 'Cantidad', 'Valor Unitario', 'Total']]
        for producto in self.productos:
            if totales_por_producto[producto['nombre']]['cantidad'] > 0:
                resumen_data.append([
                    producto['nombre'],
                    str(totales_por_producto[producto['nombre']]['cantidad']),
                    f"${producto['costo']:,}",
                    f"${totales_por_producto[producto['nombre']]['total']:,}"
                ])

        resumen_table = Table(resumen_data, colWidths=[200, 80, 100, 100])
        resumen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4D7B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#2E4D7B')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F8FB')),
        ]))
        elements.append(resumen_table)
        elements.append(Spacer(1, 20))

        # Totales
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

class MainApp(App):
    def build(self):
        self.user_store = UserStore()
        self.product_store = ProductStore()
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(PrincipalScreen(name='principal'))
        sm.add_widget(CotizacionScreen(name='cotizacion'))
        return sm

if __name__ == '__main__':
    MainApp().run()
