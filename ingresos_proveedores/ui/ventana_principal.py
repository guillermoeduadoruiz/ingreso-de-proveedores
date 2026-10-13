from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
    QStatusBar, QMenuBar, QAction, QMessageBox, QDialog,
    QLabel,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from pathlib import Path
from config.config_manager import ConfigManager
from database.sqlserver import SQLServerConnection
from database.mysql import MySQLConnection
from servicios.recepcion_svc import RecepcionService
from servicios.ingreso_svc import IngresoService
from servicios.impresion_svc import ImpresionService
from ui.seleccion_proveedor import SeleccionProveedorWidget
from ui.ingreso_remitos import IngresoRemitosWidget
from ui.registro_ingreso import RegistroIngresoWidget
from ui.consulta_ingresos import ConsultaIngresosWidget
from ui.consulta_destinatarios import ConsultaDestinatariosWidget
from ui.mateti import MatetiWidget
from ui.estilos import QSS_GLOBAL
from ui.login_dialog import LoginDialog
from ui.ui_config import ConfigDialog
from ui.config_impresion_dialog import ConfigImpresionDialog
from ui.dialogo_ayuda import DialogoAyuda, SECCIONES
from modelos.proveedor import Proveedor
from modelos.remito import Remito
from modelos.recepcion import RecepcionPrevista
from modelos.ingreso import Ingreso


class VentanaPrincipal(QMainWindow):
    PAG_SELECCION = 0
    PAG_REMITOS = 1
    PAG_REGISTRO = 2
    PAG_CONSULTA = 3
    PAG_CONSULTA_DEST = 4
    PAG_MATETI = 5

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self._cm = config_manager

        self._sqlserver_conn = SQLServerConnection(self._cm.sqlserver)
        self._mysql_conn = MySQLConnection(self._cm.mysql)

        self._recepcion_svc = RecepcionService(self._sqlserver_conn)
        self._ingreso_svc = IngresoService(self._mysql_conn)
        self._impresion_svc = ImpresionService(self._cm, self._ingreso_svc)

        self._setup_ui()
        self._recrear_servicios()
        self._remitos_pendientes: list[Remito] = []
        self._proveedor_pendiente: Proveedor | None = None

    def _setup_ui(self):
        self.setWindowTitle('Registro de Ingreso de Mercadería - Depósito')
        self.setMinimumSize(1300, 800)
        self.resize(1400, 900)
        self.setStyleSheet(QSS_GLOBAL)

        self._crear_menu()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self._crear_paginas()

        self.statusBar().showMessage('Listo')

    def _crear_menu(self):
        menubar = self.menuBar()

        menu_archivo = menubar.addMenu('Archivo')
        acc_config = QAction('Configuración...', self)
        acc_config.triggered.connect(self._abrir_configuracion)
        menu_archivo.addAction(acc_config)
        acc_impresion = QAction('Impresiones...', self)
        acc_impresion.triggered.connect(self._abrir_config_impresion)
        menu_archivo.addAction(acc_impresion)
        menu_archivo.addSeparator()
        acc_salir = QAction('Salir', self)
        acc_salir.triggered.connect(self.close)
        menu_archivo.addAction(acc_salir)

        menu_mateti = menubar.addMenu('MATETI')
        acc_mateti = QAction('Etiquetas de Materiales', self)
        acc_mateti.triggered.connect(self._ir_a_mateti)
        menu_mateti.addAction(acc_mateti)

        menu_consulta = menubar.addMenu('Consultas / Ajustar')
        acc_ver_ingresos = QAction('Ver Ingresos Realizados', self)
        acc_ver_ingresos.triggered.connect(self._ir_a_consulta)
        menu_consulta.addAction(acc_ver_ingresos)
        acc_ver_destinatarios = QAction('Ver Consulta por Destinatario', self)
        acc_ver_destinatarios.triggered.connect(self._ir_a_consulta_destinatarios)
        menu_consulta.addAction(acc_ver_destinatarios)

        menu_ayuda = menubar.addMenu('Ayuda')
        acc_manual_general = QAction('General', self)
        acc_manual_general.triggered.connect(lambda: self._abrir_ayuda('general'))
        menu_ayuda.addAction(acc_manual_general)
        acc_manual_paso1 = QAction('Paso 1 - Selección de Recepciones', self)
        acc_manual_paso1.triggered.connect(lambda: self._abrir_ayuda('paso1'))
        menu_ayuda.addAction(acc_manual_paso1)
        acc_manual_paso2 = QAction('Paso 2 - Ingreso de Remitos', self)
        acc_manual_paso2.triggered.connect(lambda: self._abrir_ayuda('paso2'))
        menu_ayuda.addAction(acc_manual_paso2)
        acc_manual_paso3 = QAction('Paso 3 - Confirmación y Registro', self)
        acc_manual_paso3.triggered.connect(lambda: self._abrir_ayuda('paso3'))
        menu_ayuda.addAction(acc_manual_paso3)
        acc_manual_consulta = QAction('Consulta de Ingresos', self)
        acc_manual_consulta.triggered.connect(lambda: self._abrir_ayuda('consulta'))
        menu_ayuda.addAction(acc_manual_consulta)
        acc_manual_config = QAction('Configuración', self)
        acc_manual_config.triggered.connect(lambda: self._abrir_ayuda('configuracion'))
        menu_ayuda.addAction(acc_manual_config)
        menu_ayuda.addSeparator()
        acc_acerca = QAction('Acerca de...', self)
        acc_acerca.triggered.connect(self._acerca_de)
        menu_ayuda.addAction(acc_acerca)

    def _crear_paginas(self):
        self.pag_seleccion = SeleccionProveedorWidget(self._recepcion_svc)
        self.pag_remitos = IngresoRemitosWidget(self._ingreso_svc)
        self.pag_registro = RegistroIngresoWidget(self._ingreso_svc, self._impresion_svc)
        self.pag_consulta = ConsultaIngresosWidget(
            self._ingreso_svc, self._cm.clave_anulacion, self._cm.sqlserver,
            self._impresion_svc,
        )
        self.pag_consulta_dest = ConsultaDestinatariosWidget(self._ingreso_svc)
        self.pag_mateti = MatetiWidget(self._sqlserver_conn, self._impresion_svc)

        self.stack.addWidget(self.pag_seleccion)
        self.stack.addWidget(self.pag_remitos)
        self.stack.addWidget(self.pag_registro)
        self.stack.addWidget(self.pag_consulta)
        self.stack.addWidget(self.pag_consulta_dest)
        self.stack.addWidget(self.pag_mateti)

        self.pag_seleccion.set_on_confirmar(self._ir_a_remitos)
        self.pag_seleccion.set_on_volver_sin_cambios(self._volver_a_remitos_sin_cambios)
        self.pag_remitos.set_on_continuar(self._ir_a_registro)
        self.pag_remitos.set_on_volver(self._ir_a_seleccion)
        self.pag_remitos.set_on_agregar_mas(self._ir_a_seleccion)
        self.pag_registro.set_on_finalizar(self._finalizar_ingreso)
        self.pag_registro.set_on_cancelar(lambda: self.stack.setCurrentIndex(self.PAG_REMITOS))
        self.pag_consulta.set_on_volver(self._ir_a_seleccion)
        self.pag_consulta_dest.set_on_volver(self._ir_a_seleccion)
        self.pag_mateti.set_on_volver(self._ir_a_seleccion)

    def _recrear_servicios(self):
        ss_config = self._cm.sqlserver
        my_config = self._cm.mysql

        self._sqlserver_conn.disconnect()
        self._mysql_conn.disconnect()

        self._sqlserver_conn = SQLServerConnection(ss_config)
        self._mysql_conn = MySQLConnection(my_config)

        if my_config.host:
            try:
                self._mysql_conn.initialize_schema()
            except Exception:
                pass

        self._recepcion_svc = RecepcionService(self._sqlserver_conn)
        self._ingreso_svc = IngresoService(self._mysql_conn)
        self._impresion_svc = ImpresionService(self._cm, self._ingreso_svc)

        for _ in range(self.stack.count()):
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        self._crear_paginas()

    def _ir_a_remitos(self, id_proveedor: str, razon_social: str, recepciones: list[RecepcionPrevista]):
        proveedor = Proveedor(
            num_proveedor=id_proveedor,
            descripcion=razon_social,
            domicilio='', codigo_postal='', ciudad='', distrito='',
        )
        vd_unit = self._cm.impresion.importe_unitario_valor_declarado
        self.pag_remitos.set_proveedor(proveedor, recepciones, vd_unit)
        if self._remitos_pendientes:
            self.pag_remitos.restaurar_remitos(self._remitos_pendientes)
            self._remitos_pendientes = []
            self._proveedor_pendiente = None
        self.stack.setCurrentIndex(self.PAG_REMITOS)
        self.statusBar().showMessage(f'Proveedor: {id_proveedor} - {razon_social}')

    def _ir_a_registro(self, remitos: list[Remito], fecha_ingreso_cd):
        proveedor = self.pag_remitos.proveedor
        self.pag_registro.set_datos(proveedor, remitos, fecha_ingreso_cd)
        self.stack.setCurrentIndex(self.PAG_REGISTRO)
        self.statusBar().showMessage('Revise y confirme el ingreso')

    def _ir_a_seleccion(self, proveedor: Proveedor | None = None, remitos: list[Remito] | None = None):
        if proveedor and remitos:
            self._remitos_pendientes = remitos[:]
            self._proveedor_pendiente = proveedor
            nombre_destino = ''
            if remitos and remitos[0].recepciones:
                nombre_destino = remitos[0].recepciones[0].nombre_destino
            self.pag_seleccion.set_prefiltro(
                proveedor.num_proveedor, nombre_destino, remitos
            )
            self.statusBar().showMessage(
                f'Agregue recepciones para {proveedor.num_proveedor} - {proveedor.descripcion}'
            )
        else:
            self._remitos_pendientes = []
            self._proveedor_pendiente = None
            self.pag_seleccion._limpiar()
            self.statusBar().showMessage('Seleccione las recepciones previstas')
        self.stack.setCurrentIndex(self.PAG_SELECCION)

    def _volver_a_remitos_sin_cambios(self):
        if self._proveedor_pendiente and self._remitos_pendientes:
            nombre_destino = ''
            if self._remitos_pendientes[0].recepciones:
                nombre_destino = self._remitos_pendientes[0].recepciones[0].nombre_destino
            recepciones = []
            for r in self._remitos_pendientes:
                recepciones.extend(r.recepciones)
            unique_recepciones = list({rp.id_recepcion: rp for rp in recepciones}.values())
            vd_unit = self._cm.impresion.importe_unitario_valor_declarado
            self.pag_remitos.set_proveedor(self._proveedor_pendiente, unique_recepciones, vd_unit)
            self.pag_remitos.restaurar_remitos(self._remitos_pendientes)
            self._remitos_pendientes = []
            self._proveedor_pendiente = None
            self.stack.setCurrentIndex(self.PAG_REMITOS)
            self.statusBar().showMessage(
                f'Proveedor: {self.pag_remitos.proveedor.num_proveedor} - {self.pag_remitos.proveedor.descripcion}'
            )

    def _finalizar_ingreso(self, ingreso: Ingreso):
        self._remitos_pendientes = []
        self._proveedor_pendiente = None
        self.pag_seleccion._limpiar()
        self.stack.setCurrentIndex(self.PAG_SELECCION)
        self.statusBar().showMessage('Listo')

    def _ir_a_consulta(self):
        self._remitos_pendientes = []
        self._proveedor_pendiente = None
        self.pag_consulta.cargar_datos()
        self.stack.setCurrentIndex(self.PAG_CONSULTA)
        self.statusBar().showMessage('Consulta de Ingresos Realizados')

    def _ir_a_mateti(self):
        self.stack.setCurrentIndex(self.PAG_MATETI)
        self.statusBar().showMessage('MATETI — Etiquetas de Materiales')

    def _ir_a_consulta_destinatarios(self):
        self._remitos_pendientes = []
        self._proveedor_pendiente = None
        self.pag_consulta_dest.cargar_datos()
        self.stack.setCurrentIndex(self.PAG_CONSULTA_DEST)
        self.statusBar().showMessage('Consulta por Destinatario')

    def _abrir_configuracion(self):
        login_dlg = LoginDialog(self._cm.sqlserver, self)
        if login_dlg.exec_() != LoginDialog.Accepted:
            return

        config_dlg = ConfigDialog(self._cm, self)
        if config_dlg.exec_() == ConfigDialog.Accepted:
            self._recrear_servicios()
            self.statusBar().showMessage('Configuración actualizada')

    def _abrir_config_impresion(self):
        login_dlg = LoginDialog(self._cm.sqlserver, self)
        if login_dlg.exec_() != LoginDialog.Accepted:
            return

        dlg = ConfigImpresionDialog(self._cm, self)
        dlg.exec_()
        self.statusBar().showMessage('Configuración de impresiones actualizada')

    def _abrir_ayuda(self, seccion: str = 'general'):
        dlg = DialogoAyuda(self)
        idx = next((i for i, (_, a) in enumerate(SECCIONES) if a == seccion), 0)
        dlg.lista_secciones.setCurrentRow(idx)
        dlg.exec_()

    def _acerca_de(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('Acerca de')
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout(dlg)
        layout.setAlignment(Qt.AlignCenter)
        
        from utils.paths import assets_dir
        logo_path = Path(assets_dir()) / 'logo-cuspide.jpg'
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            pixmap = pixmap.scaledToWidth(300, Qt.SmoothTransformation)
            lbl_logo = QLabel()
            lbl_logo.setPixmap(pixmap)
            lbl_logo.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_logo)
        
        layout.addSpacing(20)
        
        lbl_title = QLabel('Registro de Ingreso de Mercadería')
        lbl_title.setStyleSheet('font-size: 16px; font-weight: bold;')
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        layout.addSpacing(5)
        
        lbl_version = QLabel('Versión 2.0')
        lbl_version.setStyleSheet('font-size: 12px;')
        lbl_version.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_version)
        
        layout.addSpacing(10)
        
        lbl_desc = QLabel(
            'Aplicación para registrar el ingreso de mercadería '
            'asociando proveedores, remitos y recepciones previstas.'
        )
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)
        
        layout.addSpacing(10)
        
        lbl_copyright = QLabel('© Cuspide Libros')
        lbl_copyright.setStyleSheet('font-size: 10px; color: gray;')
        lbl_copyright.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_copyright)
        
        dlg.exec_()
