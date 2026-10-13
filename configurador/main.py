import sys
import os

if not getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(BASE_DIR, 'ingresos_proveedores'))

import pyodbc
import pymysql
import webbrowser

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QGroupBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QComboBox, QScrollArea, QGridLayout,
    QMessageBox, QTabWidget, QInputDialog, QSizePolicy,
)
from PyQt5.QtCore import QRegExp, Qt
from PyQt5.QtGui import QRegExpValidator

from database.conexiones import (
    ConfigSQLServer, ConfigMySQL, ConfigImpresoras,
    get_available_drivers, resolve_driver, get_driver_download_url,
)
from database.sqlserver import SQLServerConnection
from database.mysql import MySQLConnection
from utils.system_info import listar_impresoras, listar_scanners, verificar_impresora
from config.config_manager import ConfigManager


class ConfiguradorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Configurador - Ingreso de Mercadería')
        self.setMinimumSize(800, 650)
        self._cm = ConfigManager()
        self._setup_ui()
        self._cargar_config()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        tab_gen = QWidget()
        self._setup_tab_general(tab_gen)
        tabs.addTab(tab_gen, 'General')

        tab_ss = QWidget()
        self._setup_tab_sqlserver(tab_ss)
        tabs.addTab(tab_ss, 'SQL Server')

        tab_my = QWidget()
        self._setup_tab_mysql(tab_my)
        tabs.addTab(tab_my, 'MySQL')

        tab_imp = QWidget()
        self._setup_tab_impresoras(tab_imp)
        tabs.addTab(tab_imp, 'Impresoras / Scanner')

        tab_sync = QWidget()
        self._setup_tab_sincronizacion(tab_sync)
        tabs.addTab(tab_sync, 'Sincronización')

        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        self.btn_crear_tablas = QPushButton('Crear Tablas en MySQL')
        self.btn_crear_tablas.setObjectName('btnWarning')
        self.btn_crear_tablas.clicked.connect(self._crear_tablas)
        btn_layout.addWidget(self.btn_crear_tablas)

        btn_layout.addStretch()

        self.btn_guardar = QPushButton('Guardar Configuración')
        self.btn_guardar.setObjectName('btnSuccess')
        self.btn_guardar.clicked.connect(self._guardar)
        btn_layout.addWidget(self.btn_guardar)

        self.btn_salir = QPushButton('Salir')
        self.btn_salir.setObjectName('btnSecondary')
        self.btn_salir.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_salir)

        layout.addLayout(btn_layout)

    def _setup_tab_general(self, tab):
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        grp_anulacion = QGroupBox('Anulación de Ingresos')
        al = QFormLayout(grp_anulacion)
        al.setSpacing(8)

        self.txt_clave_anulacion = QLineEdit()
        self.txt_clave_anulacion.setPlaceholderText('Palabra clave para eliminar ingresos')
        al.addRow('Clave de Anulación:', self.txt_clave_anulacion)

        lbl_hint = QLabel('Si se define, aparecerá el botón "Eliminar Ingreso" en Consultas / Ajustar.')
        lbl_hint.setStyleSheet('font-size: 11px; color: #666;')
        lbl_hint.setWordWrap(True)
        al.addRow('', lbl_hint)
        layout.addWidget(grp_anulacion)

        grp_num = QGroupBox('Numeración de Remitos')
        nf = QFormLayout(grp_num)
        nf.setSpacing(8)

        self.txt_punto_venta = QLineEdit()
        self.txt_punto_venta.setPlaceholderText('00002')
        self.txt_punto_venta.setMaxLength(5)
        self.txt_punto_venta.setValidator(QRegExpValidator(QRegExp(r'^\d{0,5}$')))
        lbl_pv = QLabel(
            'Punto de venta exclusivo de esta aplicación.\n'
            'El número generado tendrá el formato: 00002 - 00003344'
        )
        lbl_pv.setStyleSheet('font-size: 11px; color: #666;')
        lbl_pv.setWordWrap(True)
        nf.addRow('Punto de venta:', self.txt_punto_venta)
        nf.addRow('', lbl_pv)

        self.spn_prox_num_remito = QSpinBox()
        self.spn_prox_num_remito.setRange(1, 99999999)
        nf.addRow('Próximo número:', self.spn_prox_num_remito)

        lbl_num = QLabel(
            'Número que recibirá el próximo remito generado.\n'
            'La aplicación lo incrementa automáticamente al emitir.'
        )
        lbl_num.setStyleSheet('font-size: 11px; color: #666;')
        lbl_num.setWordWrap(True)
        nf.addRow('', lbl_num)
        layout.addWidget(grp_num)

        layout.addStretch()

    def _setup_tab_sqlserver(self, tab):
        layout = QFormLayout(tab)
        layout.setSpacing(10)

        self.txt_ss_server = QLineEdit()
        layout.addRow('Servidor:', self.txt_ss_server)

        self.txt_ss_database = QLineEdit()
        layout.addRow('Base de Datos:', self.txt_ss_database)

        self.chk_ss_trusted = QCheckBox('Autenticación de Windows')
        self.chk_ss_trusted.setChecked(True)
        layout.addRow('', self.chk_ss_trusted)

        self.txt_ss_user = QLineEdit()
        self.txt_ss_user.setEnabled(False)
        layout.addRow('Usuario:', self.txt_ss_user)

        self.txt_ss_pass = QLineEdit()
        self.txt_ss_pass.setEchoMode(QLineEdit.Password)
        self.txt_ss_pass.setEnabled(False)
        layout.addRow('Contraseña:', self.txt_ss_pass)

        self.chk_ss_trusted.toggled.connect(self._toggle_ss_auth)

        driver_row = QHBoxLayout()
        self.cbo_ss_driver = QComboBox()
        self.cbo_ss_driver.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.cbo_ss_driver.setToolTip('Driver ODBC para SQL Server instalado en el sistema')
        driver_row.addWidget(self.cbo_ss_driver, 1)
        btn_install_driver = QPushButton('Instalar Driver')
        btn_install_driver.setObjectName('btnWarning')
        btn_install_driver.clicked.connect(self._instalar_driver_odbc)
        driver_row.addWidget(btn_install_driver)
        layout.addRow('Driver ODBC:', driver_row)

        btn_test_ss = QPushButton('Probar Conexión SQL Server')
        btn_test_ss.setObjectName('btnPrimary')
        btn_test_ss.clicked.connect(self._probar_sqlserver)
        layout.addRow('', btn_test_ss)

        self.lbl_ss_estado = QLabel('')
        self.lbl_ss_estado.setWordWrap(True)
        layout.addRow('', self.lbl_ss_estado)

    def _toggle_ss_auth(self, trusted):
        self.txt_ss_user.setEnabled(not trusted)
        self.txt_ss_pass.setEnabled(not trusted)

    def _poblar_drivers_sqlserver(self):
        self.cbo_ss_driver.clear()
        self.cbo_ss_driver.addItem('Automático (detectar)')
        for d in get_available_drivers():
            self.cbo_ss_driver.addItem(d)
        self.cbo_ss_driver.setCurrentIndex(0)

    def _setup_tab_mysql(self, tab):
        layout = QFormLayout(tab)
        layout.setSpacing(10)

        self.txt_my_host = QLineEdit()
        self.txt_my_host.setPlaceholderText('localhost')
        layout.addRow('Host:', self.txt_my_host)

        self.spn_my_port = QSpinBox()
        self.spn_my_port.setRange(1, 65535)
        self.spn_my_port.setValue(3306)
        layout.addRow('Puerto:', self.spn_my_port)

        self.txt_my_database = QLineEdit()
        layout.addRow('Base de Datos:', self.txt_my_database)

        self.txt_my_user = QLineEdit()
        layout.addRow('Usuario:', self.txt_my_user)

        self.txt_my_pass = QLineEdit()
        self.txt_my_pass.setEchoMode(QLineEdit.Password)
        layout.addRow('Contraseña:', self.txt_my_pass)

        btn_test_my = QPushButton('Probar Conexión MySQL')
        btn_test_my.setObjectName('btnPrimary')
        btn_test_my.clicked.connect(self._probar_mysql)
        layout.addRow('', btn_test_my)

        self.lbl_my_estado = QLabel('')
        layout.addRow('', self.lbl_my_estado)

    def _setup_tab_impresoras(self, tab):
        outer = QVBoxLayout(tab)
        outer.setContentsMargins(0, 0, 0, 0)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        bar.setContentsMargins(8, 8, 8, 0)
        lbl_cfg = QLabel('Configuración:')
        lbl_cfg.setStyleSheet('font-weight: bold;')
        bar.addWidget(lbl_cfg)
        self.cbo_configs = QComboBox()
        self.cbo_configs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.cbo_configs.currentIndexChanged.connect(self._on_config_cambio)
        bar.addWidget(self.cbo_configs, 1)
        btn_nueva = QPushButton('Nueva')
        btn_nueva.setObjectName('btnSuccess')
        btn_nueva.clicked.connect(self._nueva_config)
        bar.addWidget(btn_nueva)
        btn_renombrar = QPushButton('Renombrar')
        btn_renombrar.setObjectName('btnWarning')
        btn_renombrar.clicked.connect(self._renombrar_config)
        bar.addWidget(btn_renombrar)
        btn_eliminar = QPushButton('Eliminar')
        btn_eliminar.setObjectName('btnDanger')
        btn_eliminar.clicked.connect(self._eliminar_config)
        bar.addWidget(btn_eliminar)
        outer.addLayout(bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setSpacing(12)

        grp_remitos = QGroupBox('Remitos')
        glay = QFormLayout(grp_remitos)
        glay.setSpacing(8)

        imp_row = QHBoxLayout()
        imp_row.setSpacing(6)
        self.cbo_imp_remitos = QComboBox()
        self.cbo_imp_remitos.setEditable(True)
        self.cbo_imp_remitos.setPlaceholderText('Nombre de la impresora de remitos')
        imp_row.addWidget(self.cbo_imp_remitos, 1)
        btn_test_rem = QPushButton('Probar')
        btn_test_rem.setObjectName('btnWarning')
        btn_test_rem.setMaximumWidth(90)
        btn_test_rem.clicked.connect(self._probar_impresora_remitos)
        imp_row.addWidget(btn_test_rem)
        self.lbl_estado_remitos = QLabel('')
        self.lbl_estado_remitos.setStyleSheet('font-size: 11px;')
        imp_row.addWidget(self.lbl_estado_remitos, 1)
        glay.addRow('Impresora:', imp_row)

        self.cbo_papel_remitos = QComboBox()
        self.cbo_papel_remitos.addItems(ConfigImpresoras.TAMANIOS_PAPEL)
        glay.addRow('Tamaño papel:', self.cbo_papel_remitos)

        self.cbo_orientacion_remitos = QComboBox()
        self.cbo_orientacion_remitos.addItems(ConfigImpresoras.ORIENTACIONES)
        glay.addRow('Orientación:', self.cbo_orientacion_remitos)

        self.spn_copias_remitos = QSpinBox()
        self.spn_copias_remitos.setRange(1, 99)
        glay.addRow('Copias:', self.spn_copias_remitos)

        self.cbo_bandeja_remitos = QComboBox()
        self.cbo_bandeja_remitos.addItems(ConfigImpresoras.BANDEJAS)
        self.cbo_bandeja_remitos.setEditable(True)
        glay.addRow('Bandeja:', self.cbo_bandeja_remitos)

        margen_grid = QGridLayout()
        margen_grid.setSpacing(4)
        self.spn_margen_sup = QDoubleSpinBox()
        self.spn_margen_sup.setRange(0, 100)
        self.spn_margen_sup.setSuffix(' mm')
        self.spn_margen_inf = QDoubleSpinBox()
        self.spn_margen_inf.setRange(0, 100)
        self.spn_margen_inf.setSuffix(' mm')
        self.spn_margen_izq = QDoubleSpinBox()
        self.spn_margen_izq.setRange(0, 100)
        self.spn_margen_izq.setSuffix(' mm')
        self.spn_margen_der = QDoubleSpinBox()
        self.spn_margen_der.setRange(0, 100)
        self.spn_margen_der.setSuffix(' mm')
        margen_grid.addWidget(QLabel('Sup:'), 0, 0)
        margen_grid.addWidget(self.spn_margen_sup, 0, 1)
        margen_grid.addWidget(QLabel('Inf:'), 0, 2)
        margen_grid.addWidget(self.spn_margen_inf, 0, 3)
        margen_grid.addWidget(QLabel('Izq:'), 0, 4)
        margen_grid.addWidget(self.spn_margen_izq, 0, 5)
        margen_grid.addWidget(QLabel('Der:'), 0, 6)
        margen_grid.addWidget(self.spn_margen_der, 0, 7)
        glay.addRow('Márgenes:', margen_grid)

        layout.addWidget(grp_remitos)

        grp_etiquetas = QGroupBox('Etiquetas')
        ely = QFormLayout(grp_etiquetas)
        ely.setSpacing(8)

        imp_row_e = QHBoxLayout()
        imp_row_e.setSpacing(6)
        self.cbo_imp_etiquetas = QComboBox()
        self.cbo_imp_etiquetas.setEditable(True)
        self.cbo_imp_etiquetas.setPlaceholderText('Nombre de la impresora de etiquetas')
        imp_row_e.addWidget(self.cbo_imp_etiquetas, 1)
        btn_test_etq = QPushButton('Probar')
        btn_test_etq.setObjectName('btnWarning')
        btn_test_etq.setMaximumWidth(90)
        btn_test_etq.clicked.connect(self._probar_impresora_etiquetas)
        imp_row_e.addWidget(btn_test_etq)
        self.lbl_estado_etiquetas = QLabel('')
        self.lbl_estado_etiquetas.setStyleSheet('font-size: 11px;')
        imp_row_e.addWidget(self.lbl_estado_etiquetas, 1)
        ely.addRow('Impresora:', imp_row_e)

        self.cbo_tipo_etiqueta = QComboBox()
        self.cbo_tipo_etiqueta.addItems(ConfigImpresoras.TIPOS_ETIQUETA)
        self.cbo_tipo_etiqueta.currentTextChanged.connect(self._on_tipo_etiqueta_change)
        ely.addRow('Tipo etiqueta:', self.cbo_tipo_etiqueta)

        dim_grid = QGridLayout()
        dim_grid.setSpacing(4)
        self.spn_ancho_etiqueta = QDoubleSpinBox()
        self.spn_ancho_etiqueta.setRange(10, 500)
        self.spn_ancho_etiqueta.setSuffix(' mm')
        self.spn_alto_etiqueta = QDoubleSpinBox()
        self.spn_alto_etiqueta.setRange(10, 500)
        self.spn_alto_etiqueta.setSuffix(' mm')
        dim_grid.addWidget(QLabel('Ancho:'), 0, 0)
        dim_grid.addWidget(self.spn_ancho_etiqueta, 0, 1)
        dim_grid.addWidget(QLabel('Alto:'), 0, 2)
        dim_grid.addWidget(self.spn_alto_etiqueta, 0, 3)
        ely.addRow('Dimensiones:', dim_grid)

        col_grid = QGridLayout()
        col_grid.setSpacing(4)
        self.spn_columnas_etiqueta = QSpinBox()
        self.spn_columnas_etiqueta.setRange(1, 10)
        self.spn_filas_etiqueta = QSpinBox()
        self.spn_filas_etiqueta.setRange(1, 20)
        col_grid.addWidget(QLabel('Columnas:'), 0, 0)
        col_grid.addWidget(self.spn_columnas_etiqueta, 0, 1)
        col_grid.addWidget(QLabel('Filas:'), 0, 2)
        col_grid.addWidget(self.spn_filas_etiqueta, 0, 3)
        ely.addRow('Distribución:', col_grid)

        self.cbo_papel_etiquetas = QComboBox()
        self.cbo_papel_etiquetas.addItems(ConfigImpresoras.TAMANIOS_PAPEL)
        ely.addRow('Tamaño papel:', self.cbo_papel_etiquetas)

        self.cbo_bandeja_etiquetas = QComboBox()
        self.cbo_bandeja_etiquetas.addItems(ConfigImpresoras.BANDEJAS)
        self.cbo_bandeja_etiquetas.setEditable(True)
        ely.addRow('Bandeja:', self.cbo_bandeja_etiquetas)

        marg_grid = QGridLayout()
        marg_grid.setSpacing(4)
        self.spn_etq_m_sup = QDoubleSpinBox()
        self.spn_etq_m_sup.setRange(0, 100)
        self.spn_etq_m_sup.setSuffix(' mm')
        self.spn_etq_m_inf = QDoubleSpinBox()
        self.spn_etq_m_inf.setRange(0, 100)
        self.spn_etq_m_inf.setSuffix(' mm')
        self.spn_etq_m_izq = QDoubleSpinBox()
        self.spn_etq_m_izq.setRange(0, 100)
        self.spn_etq_m_izq.setSuffix(' mm')
        self.spn_etq_m_der = QDoubleSpinBox()
        self.spn_etq_m_der.setRange(0, 100)
        self.spn_etq_m_der.setSuffix(' mm')
        self.spn_etq_sep = QDoubleSpinBox()
        self.spn_etq_sep.setRange(0, 100)
        self.spn_etq_sep.setSuffix(' mm')
        marg_grid.addWidget(QLabel('Sup.:'), 0, 0)
        marg_grid.addWidget(self.spn_etq_m_sup, 0, 1)
        marg_grid.addWidget(QLabel('Inf.:'), 0, 2)
        marg_grid.addWidget(self.spn_etq_m_inf, 0, 3)
        marg_grid.addWidget(QLabel('Izq.:'), 1, 0)
        marg_grid.addWidget(self.spn_etq_m_izq, 1, 1)
        marg_grid.addWidget(QLabel('Der.:'), 1, 2)
        marg_grid.addWidget(self.spn_etq_m_der, 1, 3)
        marg_grid.addWidget(QLabel('Entre etiquetas:'), 2, 0)
        marg_grid.addWidget(self.spn_etq_sep, 2, 1)
        ely.addRow('Márgenes etiqueta:', marg_grid)

        layout.addWidget(grp_etiquetas)

        grp_scanner = QGroupBox('Scanner')
        sly = QFormLayout(grp_scanner)
        self.cbo_scanner = QComboBox()
        self.cbo_scanner.setEditable(True)
        self.cbo_scanner.setPlaceholderText('Nombre o identificador del scanner')
        sly.addRow('Scanner:', self.cbo_scanner)
        layout.addWidget(grp_scanner)

        self._poblar_dispositivos()
        layout.addStretch()
        scroll.setWidget(inner)

        outer.addWidget(scroll)

    def _poblar_dispositivos(self):
        self.cbo_imp_remitos.addItems(listar_impresoras())
        self.cbo_imp_etiquetas.addItems(listar_impresoras())
        scanners = listar_scanners()
        if scanners:
            self.cbo_scanner.addItems(scanners)

    def _recargar_lista_configs(self):
        self.cbo_configs.blockSignals(True)
        self.cbo_configs.clear()
        self.cbo_configs.addItems(self._cm.get_printer_config_names())
        idx = self.cbo_configs.findText(self._cm.impresora_activa)
        if idx >= 0:
            self.cbo_configs.setCurrentIndex(idx)
        elif self.cbo_configs.count() > 0:
            self.cbo_configs.setCurrentIndex(0)
        self.cbo_configs.blockSignals(False)

    def _guardar_config_actual_en_cm(self):
        cfg = self._get_printer_config()
        self._cm.save_printer_config(cfg, name=self._cm.impresora_activa)

    def _cargar_config_en_formulario(self, nombre: str):
        cfg = self._cm.get_printer_config(nombre)
        if cfg is None:
            return
        idx = self.cbo_imp_remitos.findText(cfg.impresora_remitos)
        if idx >= 0:
            self.cbo_imp_remitos.setCurrentIndex(idx)
        elif cfg.impresora_remitos:
            self.cbo_imp_remitos.setEditText(cfg.impresora_remitos)
        idx = self.cbo_papel_remitos.findText(cfg.tamanio_papel_remitos)
        if idx >= 0:
            self.cbo_papel_remitos.setCurrentIndex(idx)
        idx = self.cbo_orientacion_remitos.findText(cfg.orientacion_remitos)
        if idx >= 0:
            self.cbo_orientacion_remitos.setCurrentIndex(idx)
        self.spn_copias_remitos.setValue(cfg.copias_remitos)
        idx = self.cbo_bandeja_remitos.findText(cfg.bandeja_remitos)
        if idx >= 0:
            self.cbo_bandeja_remitos.setCurrentIndex(idx)
        else:
            self.cbo_bandeja_remitos.setEditText(cfg.bandeja_remitos)
        self.spn_margen_sup.setValue(cfg.margen_superior_remitos)
        self.spn_margen_inf.setValue(cfg.margen_inferior_remitos)
        self.spn_margen_izq.setValue(cfg.margen_izquierdo_remitos)
        self.spn_margen_der.setValue(cfg.margen_derecho_remitos)

        idx = self.cbo_imp_etiquetas.findText(cfg.impresora_etiquetas)
        if idx >= 0:
            self.cbo_imp_etiquetas.setCurrentIndex(idx)
        elif cfg.impresora_etiquetas:
            self.cbo_imp_etiquetas.setEditText(cfg.impresora_etiquetas)
        idx = self.cbo_tipo_etiqueta.findText(cfg.tipo_etiqueta)
        if idx >= 0:
            self.cbo_tipo_etiqueta.setCurrentIndex(idx)
        elif cfg.tipo_etiqueta:
            self.cbo_tipo_etiqueta.setEditText(cfg.tipo_etiqueta)
        self.spn_ancho_etiqueta.setValue(cfg.ancho_etiqueta)
        self.spn_alto_etiqueta.setValue(cfg.alto_etiqueta)
        self.spn_columnas_etiqueta.setValue(cfg.columnas_etiqueta)
        self.spn_filas_etiqueta.setValue(cfg.filas_etiqueta)
        idx = self.cbo_papel_etiquetas.findText(cfg.tamanio_papel_etiquetas)
        if idx >= 0:
            self.cbo_papel_etiquetas.setCurrentIndex(idx)
        idx = self.cbo_bandeja_etiquetas.findText(cfg.bandeja_etiquetas)
        if idx >= 0:
            self.cbo_bandeja_etiquetas.setCurrentIndex(idx)
        else:
            self.cbo_bandeja_etiquetas.setEditText(cfg.bandeja_etiquetas)
        self.spn_etq_m_sup.setValue(cfg.margen_superior_etiquetas)
        self.spn_etq_m_inf.setValue(cfg.margen_inferior_etiquetas)
        self.spn_etq_m_izq.setValue(cfg.margen_izquierdo_etiquetas)
        self.spn_etq_m_der.setValue(cfg.margen_derecho_etiquetas)
        self.spn_etq_sep.setValue(cfg.separacion_etiquetas)

        idx = self.cbo_scanner.findText(cfg.scanner)
        if idx >= 0:
            self.cbo_scanner.setCurrentIndex(idx)
        elif cfg.scanner:
            self.cbo_scanner.setEditText(cfg.scanner)

    def _on_config_cambio(self, idx: int):
        if idx < 0:
            return
        nombre = self.cbo_configs.currentText()
        if nombre and nombre != self._cm.impresora_activa:
            self._cm.set_active_config(nombre)
            self._cargar_config_en_formulario(nombre)

    def _nueva_config(self):
        nombre, ok = QInputDialog.getText(
            self, 'Nueva Configuración', 'Nombre de la nueva configuración:'
        )
        if not ok or not nombre.strip():
            return
        nombre = nombre.strip()
        if nombre in self._cm.get_printer_config_names():
            QMessageBox.warning(self, 'Error', 'Ya existe una configuración con ese nombre.')
            return
        nueva = ConfigImpresoras()
        self._cm.save_printer_config(nueva, name=nombre)
        self._recargar_lista_configs()
        idx = self.cbo_configs.findText(nombre)
        if idx >= 0:
            self.cbo_configs.setCurrentIndex(idx)

    def _renombrar_config(self):
        actual = self._cm.impresora_activa
        nombre, ok = QInputDialog.getText(
            self, 'Renombrar Configuración',
            'Nuevo nombre:',
            text=actual,
        )
        if not ok or not nombre.strip():
            return
        nombre = nombre.strip()
        if nombre == actual:
            return
        if nombre in self._cm.get_printer_config_names():
            QMessageBox.warning(self, 'Error', 'Ya existe una configuración con ese nombre.')
            return
        self._cm.rename_printer_config(actual, nombre)
        self._recargar_lista_configs()

    def _eliminar_config(self):
        nombres = self._cm.get_printer_config_names()
        if len(nombres) <= 1:
            QMessageBox.warning(self, 'Error', 'No se puede eliminar la única configuración.')
            return
        resp = QMessageBox.question(
            self, 'Eliminar Configuración',
            f'¿Eliminar la configuración "{self._cm.impresora_activa}"?',
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        self._cm.delete_printer_config(self._cm.impresora_activa)
        self._recargar_lista_configs()
        self._cargar_config_en_formulario(self._cm.impresora_activa)

    def _on_tipo_etiqueta_change(self, tipo: str):
        preset = {
            '2 x 1 (99.1 x 42.3 mm)': (99.1, 42.3, 2, 1),
            '3 x 1 (66.0 x 42.3 mm)': (66.0, 42.3, 3, 1),
            '4 x 2 (49.0 x 25.4 mm)': (49.0, 25.4, 4, 2),
            '4 x 1 (49.0 x 42.3 mm)': (49.0, 42.3, 4, 1),
            '2 x 2 (99.1 x 25.4 mm)': (99.1, 25.4, 2, 2),
        }
        if tipo in preset:
            ancho, alto, cols, filas = preset[tipo]
            self.spn_ancho_etiqueta.setValue(ancho)
            self.spn_alto_etiqueta.setValue(alto)
            self.spn_columnas_etiqueta.setValue(cols)
            self.spn_filas_etiqueta.setValue(filas)

    def _probar_impresora_remitos(self):
        nombre = self.cbo_imp_remitos.currentText().strip()
        ok, msg = verificar_impresora(nombre)
        self.lbl_estado_remitos.setStyleSheet(
            f'color: {"green" if ok else "red"}; font-size: 11px; font-weight: bold;'
        )
        self.lbl_estado_remitos.setText(msg)

    def _probar_impresora_etiquetas(self):
        nombre = self.cbo_imp_etiquetas.currentText().strip()
        ok, msg = verificar_impresora(nombre)
        self.lbl_estado_etiquetas.setStyleSheet(
            f'color: {"green" if ok else "red"}; font-size: 11px; font-weight: bold;'
        )
        self.lbl_estado_etiquetas.setText(msg)

    def _cargar_config(self):
        self._cm.load_config()
        self.txt_clave_anulacion.setText(self._cm.clave_anulacion)
        self.txt_punto_venta.setText(self._cm.impresion.punto_venta)
        self.spn_prox_num_remito.setValue(self._cm.impresion.prox_numero_remito)
        self._poblar_drivers_sqlserver()

        ss = self._cm.sqlserver
        self.txt_ss_server.setText(ss.server)
        self.txt_ss_database.setText(ss.database)
        self.chk_ss_trusted.setChecked(ss.trusted)
        self.txt_ss_user.setText(ss.username)
        self.txt_ss_pass.setText(ss.password)
        if ss.driver:
            idx = self.cbo_ss_driver.findText(ss.driver)
            if idx >= 0:
                self.cbo_ss_driver.setCurrentIndex(idx)

        my = self._cm.mysql
        self.txt_my_host.setText(my.host)
        self.spn_my_port.setValue(my.port)
        self.txt_my_database.setText(my.database)
        self.txt_my_user.setText(my.username)
        self.txt_my_pass.setText(my.password)

        self._recargar_lista_configs()
        self._cargar_config_en_formulario(self._cm.impresora_activa)

    def _get_ss_config(self) -> dict:
        driver = self.cbo_ss_driver.currentText()
        if driver == 'Automático (detectar)':
            driver = ''
        return {
            'server': self.txt_ss_server.text().strip(),
            'database': self.txt_ss_database.text().strip(),
            'trusted': self.chk_ss_trusted.isChecked(),
            'username': self.txt_ss_user.text().strip(),
            'password': self.txt_ss_pass.text(),
            'driver': driver,
        }

    def _get_my_config(self) -> dict:
        return {
            'host': self.txt_my_host.text().strip(),
            'port': self.spn_my_port.value(),
            'database': self.txt_my_database.text().strip(),
            'username': self.txt_my_user.text().strip(),
            'password': self.txt_my_pass.text(),
        }

    def _get_printer_config(self) -> dict:
        return {
            'impresora_remitos': self.cbo_imp_remitos.currentText().strip(),
            'tamanio_papel_remitos': self.cbo_papel_remitos.currentText(),
            'orientacion_remitos': self.cbo_orientacion_remitos.currentText(),
            'copias_remitos': self.spn_copias_remitos.value(),
            'bandeja_remitos': self.cbo_bandeja_remitos.currentText().strip(),
            'margen_superior_remitos': self.spn_margen_sup.value(),
            'margen_inferior_remitos': self.spn_margen_inf.value(),
            'margen_izquierdo_remitos': self.spn_margen_izq.value(),
            'margen_derecho_remitos': self.spn_margen_der.value(),
            'impresora_etiquetas': self.cbo_imp_etiquetas.currentText().strip(),
            'tipo_etiqueta': self.cbo_tipo_etiqueta.currentText().strip(),
            'ancho_etiqueta': self.spn_ancho_etiqueta.value(),
            'alto_etiqueta': self.spn_alto_etiqueta.value(),
            'columnas_etiqueta': self.spn_columnas_etiqueta.value(),
            'filas_etiqueta': self.spn_filas_etiqueta.value(),
            'tamanio_papel_etiquetas': self.cbo_papel_etiquetas.currentText(),
            'bandeja_etiquetas': self.cbo_bandeja_etiquetas.currentText().strip(),
            'margen_superior_etiquetas': self.spn_etq_m_sup.value(),
            'margen_inferior_etiquetas': self.spn_etq_m_inf.value(),
            'margen_izquierdo_etiquetas': self.spn_etq_m_izq.value(),
            'margen_derecho_etiquetas': self.spn_etq_m_der.value(),
            'separacion_etiquetas': self.spn_etq_sep.value(),
            'scanner': self.cbo_scanner.currentText().strip(),
        }

    def _probar_sqlserver(self):
        cfg = self._get_ss_config()
        if not cfg['server'] or not cfg['database']:
            QMessageBox.warning(self, 'Error', 'Complete Servidor y Base de Datos.')
            return
        from database.conexiones import build_connection_str, test_drivers
        driver = cfg.get('driver', '')
        try:
            conn_str = build_connection_str(
                server=cfg['server'],
                database=cfg['database'],
                trusted=cfg['trusted'],
                username=cfg['username'],
                password=cfg['password'],
                driver=driver,
            )
            conn = pyodbc.connect(conn_str, timeout=5)
            conn.close()
            self.lbl_ss_estado.setStyleSheet('color: green; font-weight: bold;')
            self.lbl_ss_estado.setText(
                f'Conexión exitosa con {self._get_driver_display(driver)}.'
            )
        except RuntimeError as e:
            if 'no encontrado' in str(e):
                ok, err, good_driver = test_drivers(
                    server=cfg['server'], database=cfg['database'],
                    trusted=cfg['trusted'], username=cfg['username'], password=cfg['password'],
                )
                if ok:
                    self.cbo_ss_driver.setCurrentText(good_driver)
                    self.lbl_ss_estado.setStyleSheet('color: green; font-weight: bold;')
                    self.lbl_ss_estado.setText(f'Conexión exitosa con {good_driver}.')
                    return
            self.lbl_ss_estado.setStyleSheet('color: red; font-weight: bold;')
            self.lbl_ss_estado.setText(str(e))
        except Exception as e:
            self.lbl_ss_estado.setStyleSheet('color: red; font-weight: bold;')
            msg = str(e)
            if 'IM002' in msg:
                msg = (
                    'Driver ODBC no instalado.\n'
                    f'Haga clic en "Instalar Driver" o descargue desde:\n'
                    f'{get_driver_download_url()}'
                )
            self.lbl_ss_estado.setText(msg)

    def _get_driver_display(self, driver: str) -> str:
        return driver if driver else 'driver detectado automáticamente'

    def _instalar_driver_odbc(self):
        url = get_driver_download_url()
        try:
            webbrowser.open(url)
        except Exception:
            QMessageBox.information(
                self, 'Descargar Driver ODBC',
                f'Abra el siguiente enlace en su navegador:\n\n{url}'
            )

    def _probar_mysql(self):
        cfg = self._get_my_config()
        if not cfg['host'] or not cfg['database']:
            QMessageBox.warning(self, 'Error', 'Complete Host y Base de Datos.')
            return
        try:
            conn = pymysql.connect(
                host=cfg['host'],
                port=cfg['port'],
                user=cfg['username'],
                password=cfg['password'],
                database=cfg['database'],
                charset='utf8mb4',
                connect_timeout=5,
                ssl_disabled=True,
            )
            conn.close()
            self.lbl_my_estado.setStyleSheet('color: green; font-weight: bold;')
            self.lbl_my_estado.setText('Conexión exitosa.')
        except Exception as e:
            self.lbl_my_estado.setStyleSheet('color: red; font-weight: bold;')
            self.lbl_my_estado.setText(f'Error: {str(e)[:80]}')

    def _initialize_schema(self, conn):
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd (
                    id_ingreso VARCHAR(50) PRIMARY KEY,
                    fecha_ingreso DATE NOT NULL,
                    num_proveedor VARCHAR(20) NOT NULL,
                    razon_social VARCHAR(200) NOT NULL,
                    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd_remitos (
                    id_remito INT AUTO_INCREMENT PRIMARY KEY,
                    id_ingreso VARCHAR(50) NOT NULL,
                    num_remito VARCHAR(50) NOT NULL,
                    fecha_remito DATE NOT NULL,
                    cantidad_bultos INT NOT NULL,
                    cantidad_unidades INT NOT NULL DEFAULT 0,
                    num_proveedor VARCHAR(20) NOT NULL,
                    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_ingreso) REFERENCES ingresoscd(id_ingreso),
                    UNIQUE KEY uq_remito_proveedor (num_remito, num_proveedor)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd_remito_recepciones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_remito INT NOT NULL,
                    id_recepcion_prevista VARCHAR(50) NOT NULL,
                    sucursal_destino VARCHAR(50) NOT NULL DEFAULT '',
                    FOREIGN KEY (id_remito) REFERENCES ingresoscd_remitos(id_remito) ON DELETE CASCADE,
                    UNIQUE KEY uq_remito_recepcion (id_remito, id_recepcion_prevista)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')

    def _crear_tablas(self):
        cfg = self._get_my_config()
        if not cfg['host'] or not cfg['database']:
            QMessageBox.warning(self, 'Error', 'Configure la conexión MySQL primero.')
            return
        try:
            conn = pymysql.connect(
                host=cfg['host'],
                port=cfg['port'],
                user=cfg['username'],
                password=cfg['password'],
                database=cfg['database'],
                charset='utf8mb4',
                autocommit=True,
                connect_timeout=5,
                ssl_disabled=True,
            )
            self._initialize_schema(conn)
            conn.close()
            QMessageBox.information(self, 'Éxito', 'Tablas creadas correctamente en MySQL.')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error al crear tablas:\n{str(e)[:200]}')

    def _guardar(self):
        ss = self._get_ss_config()
        my = self._get_my_config()

        if not ss['server'] or not ss['database']:
            QMessageBox.warning(self, 'Validación', 'Complete los datos de SQL Server.')
            return
        if not my['host'] or not my['database']:
            QMessageBox.warning(self, 'Validación', 'Complete los datos de MySQL.')
            return

        self._cm.clave_anulacion = self.txt_clave_anulacion.text().strip()
        self._cm.impresion.punto_venta = self.txt_punto_venta.text().strip()
        self._cm.impresion.prox_numero_remito = self.spn_prox_num_remito.value()
        self._cm.save_sqlserver_config(ConfigSQLServer(**ss))
        self._cm.save_mysql_config(ConfigMySQL(**my))
        self._cm.save_impresion_config(self._cm.impresion)
        self._guardar_config_actual_en_cm()

        QMessageBox.information(
            self, 'Configuración Guardada',
            'Configuración guardada correctamente.\n\nAhora puede ejecutar la aplicación principal.'
        )

    def _setup_tab_sincronizacion(self, tab):
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        lbl = QLabel(
            'Sincroniza datos maestros desde SQL Server hacia MySQL.\n'
            'Esto permite que la aplicación web acceda a toda la información sin conectar a SQL Server.'
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        grp_destinos = QGroupBox('Nombres de Destino (Sucursales)')
        grp_destinos_layout = QVBoxLayout(grp_destinos)
        lbl_dest = QLabel(
            'Actualiza nombre_destino, domicilio, código postal, ciudad y distrito\n'
            'en ingresoscd_remito_recepciones donde estén vacíos.'
        )
        lbl_dest.setWordWrap(True)
        grp_destinos_layout.addWidget(lbl_dest)
        btn_destinos = QPushButton('Sincronizar Nombres Destino')
        btn_destinos.clicked.connect(self._sincronizar_nombres_destino)
        grp_destinos_layout.addWidget(btn_destinos)
        self.lblResultadoDestinos = QLabel('')
        grp_destinos_layout.addWidget(self.lblResultadoDestinos)
        layout.addWidget(grp_destinos)

        grp_proveedores = QGroupBox('Razón Social de Proveedores')
        grp_proveedores_layout = QVBoxLayout(grp_proveedores)
        lbl_prov = QLabel(
            'Actualiza razon_social en ingresoscd donde esté vacía.'
        )
        lbl_prov.setWordWrap(True)
        grp_proveedores_layout.addWidget(lbl_prov)
        btn_proveedores = QPushButton('Sincronizar Razón Social Proveedores')
        btn_proveedores.clicked.connect(self._sincronizar_razon_social)
        grp_proveedores_layout.addWidget(btn_proveedores)
        self.lblResultadoProveedores = QLabel('')
        grp_proveedores_layout.addWidget(self.lblResultadoProveedores)
        layout.addWidget(grp_proveedores)

        layout.addStretch()

    def _get_config_from_form(self) -> tuple[dict | None, dict | None]:
        ss = self._get_ss_config()
        if not ss['server'] or not ss['database']:
            QMessageBox.warning(self, 'Validación', 'Complete los datos de SQL Server.')
            return None, None
        my = self._get_my_config()
        if not my['host'] or not my['database']:
            QMessageBox.warning(self, 'Validación', 'Complete los datos de MySQL.')
            return None, None
        return ss, my

    def _sincronizar_nombres_destino(self):
        ss, my = self._get_config_from_form()
        if not ss or not my:
            return
        self.lblResultadoDestinos.setText('Conectando...')
        QApplication.processEvents()
        try:
            ss_conn = SQLServerConnection(ConfigSQLServer(**ss))
            ss_conn.connect()
            my_conn = MySQLConnection(ConfigMySQL(**my))
            my_conn.connect()
            resultado = my_conn.sincronizar_nombres_destino(ss_conn)
            ss_conn.disconnect()
            my_conn.disconnect()
            total = resultado['actualizados']
            no_enc = resultado['no_encontrados']
            self.lblResultadoDestinos.setText(
                f'Listo: {total} registros actualizados, {no_enc} sucursales no encontradas en SQL Server.'
            )
            QMessageBox.information(
                self, 'Sincronización Completada',
                f'Nombres de destino sincronizados.\n\n'
                f'Registros actualizados: {total}\n'
                f'Sucursales no encontradas: {no_enc}\n'
                f'Total sucursales vacías: {resultado["total_sucursales"]}'
            )
        except Exception as e:
            self.lblResultadoDestinos.setText(f'Error: {e}')
            QMessageBox.critical(self, 'Error de Sincronización', f'Error al sincronizar:\n{e}')

    def _sincronizar_razon_social(self):
        ss, my = self._get_config_from_form()
        if not ss or not my:
            return
        self.lblResultadoProveedores.setText('Conectando...')
        QApplication.processEvents()
        try:
            ss_conn = SQLServerConnection(ConfigSQLServer(**ss))
            ss_conn.connect()
            my_conn = MySQLConnection(ConfigMySQL(**my))
            my_conn.connect()
            resultado = my_conn.sincronizar_razon_social_proveedores(ss_conn)
            ss_conn.disconnect()
            my_conn.disconnect()
            total = resultado['actualizados']
            no_enc = resultado['no_encontrados']
            self.lblResultadoProveedores.setText(
                f'Listo: {total} registros actualizados, {no_enc} proveedores no encontrados en SQL Server.'
            )
            QMessageBox.information(
                self, 'Sincronización Completada',
                f'Razón social de proveedores sincronizada.\n\n'
                f'Registros actualizados: {total}\n'
                f'Proveedores no encontrados: {no_enc}\n'
                f'Total proveedores vacíos: {resultado["total_proveedores"]}'
            )
        except Exception as e:
            self.lblResultadoProveedores.setText(f'Error: {e}')
            QMessageBox.critical(self, 'Error de Sincronización', f'Error al sincronizar:\n{e}')


def main():
    import traceback
    try:
        app = QApplication(sys.argv)
        app.setApplicationName('Configurador - Ingreso de Mercadería')
        w = ConfiguradorApp()
        w.show()
        sys.exit(app.exec_())
    except Exception:
        traceback.print_exc()
        raise


if __name__ == '__main__':
    main()
