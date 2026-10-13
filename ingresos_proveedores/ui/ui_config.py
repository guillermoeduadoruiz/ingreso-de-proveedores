import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTabWidget, QWidget, QCheckBox,
    QSpinBox, QDoubleSpinBox, QComboBox, QScrollArea,
    QMessageBox, QFormLayout, QGridLayout, QInputDialog, QSizePolicy,
)
from PyQt5.QtCore import Qt
from database.conexiones import (
    ConfigSQLServer, ConfigMySQL, ConfigImpresoras,
    get_available_drivers, get_driver_download_url, build_connection_str,
)
from config.config_manager import ConfigManager
from utils.system_info import listar_impresoras, listar_scanners, verificar_impresora


class ConfigDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._cm = config_manager
        self.setWindowTitle('Configuración de la Aplicación')
        self.setMinimumSize(800, 650)
        self._setup_ui()
        self._cargar_datos()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.tab_sqlserver = QWidget()
        self.tab_mysql = QWidget()
        self.tab_impresoras = QWidget()
        self.tabs.addTab(self.tab_sqlserver, 'SQL Server')
        self.tabs.addTab(self.tab_mysql, 'MySQL')
        self.tabs.addTab(self.tab_impresoras, 'Impresoras / Scanner')

        self._setup_tab_sqlserver()
        self._setup_tab_mysql()
        self._setup_tab_impresoras()

        layout.addWidget(self.tabs, 1)

        buttons = QHBoxLayout()
        self.btn_probar_sql = QPushButton('Probar SQL Server')
        self.btn_probar_sql.setObjectName('btnWarning')
        buttons.addWidget(self.btn_probar_sql)
        self.btn_probar_mysql = QPushButton('Probar MySQL')
        self.btn_probar_mysql.setObjectName('btnWarning')
        buttons.addWidget(self.btn_probar_mysql)
        buttons.addStretch()
        self.btn_guardar = QPushButton('Guardar Configuración')
        self.btn_guardar.setObjectName('btnSuccess')
        buttons.addWidget(self.btn_guardar)
        self.btn_cerrar = QPushButton('Cerrar')
        self.btn_cerrar.setObjectName('btnSecondary')
        buttons.addWidget(self.btn_cerrar)
        layout.addLayout(buttons)

        self.btn_guardar.clicked.connect(self._guardar)
        self.btn_cerrar.clicked.connect(self.reject)
        self.btn_probar_sql.clicked.connect(self._probar_sqlserver)
        self.btn_probar_mysql.clicked.connect(self._probar_mysql)

    def _setup_tab_sqlserver(self):
        layout = QFormLayout(self.tab_sqlserver)
        layout.setSpacing(10)

        self.txt_ss_server = QLineEdit()
        layout.addRow('Servidor:', self.txt_ss_server)

        self.txt_ss_database = QLineEdit()
        layout.addRow('Base de Datos:', self.txt_ss_database)

        self.chk_ss_trusted = QCheckBox('Autenticación de Windows')
        self.chk_ss_trusted.setChecked(True)
        layout.addRow('', self.chk_ss_trusted)

        self.txt_ss_user = QLineEdit()
        layout.addRow('Usuario:', self.txt_ss_user)

        self.txt_ss_pass = QLineEdit()
        self.txt_ss_pass.setEchoMode(QLineEdit.Password)
        layout.addRow('Contraseña:', self.txt_ss_pass)

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

        self.lbl_ss_estado = QLabel('')
        self.lbl_ss_estado.setWordWrap(True)
        layout.addRow('', self.lbl_ss_estado)

        self.chk_ss_trusted.toggled.connect(self._toggle_sqlserver_auth)

    def _toggle_sqlserver_auth(self, trusted: bool):
        self.txt_ss_user.setEnabled(not trusted)
        self.txt_ss_pass.setEnabled(not trusted)

    def _setup_tab_mysql(self):
        layout = QFormLayout(self.tab_mysql)
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

        self.lbl_my_estado = QLabel('')
        layout.addRow('', self.lbl_my_estado)

    def _setup_tab_impresoras(self):
        outer = QVBoxLayout(self.tab_impresoras)
        outer.setContentsMargins(0, 0, 0, 0)

        # ---- selector de configuracion ----
        bar = QHBoxLayout()
        bar.setSpacing(6)
        bar.setContentsMargins(8, 8, 8, 0)
        lbl_cfg = QLabel('Configuración:')
        lbl_cfg.setStyleSheet('font-weight: bold;')
        bar.addWidget(lbl_cfg)
        self.cbo_configs = QComboBox()
        self.cbo_configs.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )
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

        # ---- Remitos ----
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

        # ---- Etiquetas ----
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

        # ---- Etiquetas MATETI ----
        grp_mateti = QGroupBox('Etiquetas MATETI')
        mly = QFormLayout(grp_mateti)
        mly.setSpacing(8)

        imp_row_m = QHBoxLayout()
        imp_row_m.setSpacing(6)
        self.cbo_imp_etq_mateti = QComboBox()
        self.cbo_imp_etq_mateti.setEditable(True)
        self.cbo_imp_etq_mateti.setPlaceholderText('Nombre de la impresora MATETI')
        imp_row_m.addWidget(self.cbo_imp_etq_mateti, 1)
        btn_test_mateti = QPushButton('Probar')
        btn_test_mateti.setObjectName('btnWarning')
        btn_test_mateti.setMaximumWidth(90)
        btn_test_mateti.clicked.connect(self._probar_impresora_mateti)
        imp_row_m.addWidget(btn_test_mateti)
        self.lbl_estado_mateti = QLabel('')
        self.lbl_estado_mateti.setStyleSheet('font-size: 11px;')
        imp_row_m.addWidget(self.lbl_estado_mateti, 1)
        mly.addRow('Impresora:', imp_row_m)

        dim_grid_m = QGridLayout()
        dim_grid_m.setSpacing(4)
        self.spn_ancho_etq_mateti = QDoubleSpinBox()
        self.spn_ancho_etq_mateti.setRange(10, 500)
        self.spn_ancho_etq_mateti.setSuffix(' mm')
        self.spn_alto_etq_mateti = QDoubleSpinBox()
        self.spn_alto_etq_mateti.setRange(10, 500)
        self.spn_alto_etq_mateti.setSuffix(' mm')
        dim_grid_m.addWidget(QLabel('Ancho:'), 0, 0)
        dim_grid_m.addWidget(self.spn_ancho_etq_mateti, 0, 1)
        dim_grid_m.addWidget(QLabel('Alto:'), 0, 2)
        dim_grid_m.addWidget(self.spn_alto_etq_mateti, 0, 3)
        mly.addRow('Tamaño etiqueta:', dim_grid_m)

        col_grid_m = QGridLayout()
        col_grid_m.setSpacing(4)
        self.spn_columnas_etq_mateti = QSpinBox()
        self.spn_columnas_etq_mateti.setRange(1, 10)
        self.spn_sep_etq_mateti = QDoubleSpinBox()
        self.spn_sep_etq_mateti.setRange(0, 100)
        self.spn_sep_etq_mateti.setSuffix(' mm')
        col_grid_m.addWidget(QLabel('Columnas:'), 0, 0)
        col_grid_m.addWidget(self.spn_columnas_etq_mateti, 0, 1)
        col_grid_m.addWidget(QLabel('Separación:'), 0, 2)
        col_grid_m.addWidget(self.spn_sep_etq_mateti, 0, 3)
        mly.addRow('Distribución:', col_grid_m)

        marg_grid_m = QGridLayout()
        marg_grid_m.setSpacing(4)
        self.spn_mateti_m_sup = QDoubleSpinBox()
        self.spn_mateti_m_sup.setRange(0, 100)
        self.spn_mateti_m_sup.setSuffix(' mm')
        self.spn_mateti_m_inf = QDoubleSpinBox()
        self.spn_mateti_m_inf.setRange(0, 100)
        self.spn_mateti_m_inf.setSuffix(' mm')
        self.spn_mateti_m_izq = QDoubleSpinBox()
        self.spn_mateti_m_izq.setRange(0, 100)
        self.spn_mateti_m_izq.setSuffix(' mm')
        self.spn_mateti_m_der = QDoubleSpinBox()
        self.spn_mateti_m_der.setRange(0, 100)
        self.spn_mateti_m_der.setSuffix(' mm')
        marg_grid_m.addWidget(QLabel('Sup.:'), 0, 0)
        marg_grid_m.addWidget(self.spn_mateti_m_sup, 0, 1)
        marg_grid_m.addWidget(QLabel('Inf.:'), 0, 2)
        marg_grid_m.addWidget(self.spn_mateti_m_inf, 0, 3)
        marg_grid_m.addWidget(QLabel('Izq.:'), 1, 0)
        marg_grid_m.addWidget(self.spn_mateti_m_izq, 1, 1)
        marg_grid_m.addWidget(QLabel('Der.:'), 1, 2)
        marg_grid_m.addWidget(self.spn_mateti_m_der, 1, 3)
        mly.addRow('Márgenes:', marg_grid_m)

        layout.addWidget(grp_mateti)

        # ---- Scanner ----
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
        impresoras = listar_impresoras()
        self.cbo_imp_remitos.addItems(impresoras)
        self.cbo_imp_etiquetas.addItems(impresoras)
        self.cbo_imp_etq_mateti.addItems(impresoras)
        scanners = listar_scanners()
        if scanners:
            self.cbo_scanner.addItems(scanners)

    def _recargar_lista_configs(self):
        actual = self.cbo_configs.currentText()
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

        idx = self.cbo_imp_etq_mateti.findText(cfg.impresora_etiquetas_mateti)
        if idx >= 0:
            self.cbo_imp_etq_mateti.setCurrentIndex(idx)
        elif cfg.impresora_etiquetas_mateti:
            self.cbo_imp_etq_mateti.setEditText(cfg.impresora_etiquetas_mateti)
        self.spn_ancho_etq_mateti.setValue(cfg.ancho_etiqueta_mateti)
        self.spn_alto_etq_mateti.setValue(cfg.alto_etiqueta_mateti)
        self.spn_columnas_etq_mateti.setValue(cfg.columnas_etiqueta_mateti)
        self.spn_sep_etq_mateti.setValue(cfg.separacion_etiqueta_mateti)
        self.spn_mateti_m_sup.setValue(cfg.margen_superior_etiquetas_mateti)
        self.spn_mateti_m_inf.setValue(cfg.margen_inferior_etiquetas_mateti)
        self.spn_mateti_m_izq.setValue(cfg.margen_izquierdo_etiquetas_mateti)
        self.spn_mateti_m_der.setValue(cfg.margen_derecho_etiquetas_mateti)

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

    def _probar_impresora_mateti(self):
        nombre = self.cbo_imp_etq_mateti.currentText().strip()
        ok, msg = verificar_impresora(nombre)
        self.lbl_estado_mateti.setStyleSheet(
            f'color: {"green" if ok else "red"}; font-size: 11px; font-weight: bold;'
        )
        self.lbl_estado_mateti.setText(msg)

    def _cargar_datos(self):
        self._poblar_drivers_sqlserver()
        cfg = self._cm.sqlserver
        self.txt_ss_server.setText(cfg.server)
        self.txt_ss_database.setText(cfg.database)
        self.chk_ss_trusted.setChecked(cfg.trusted)
        self.txt_ss_user.setText(cfg.username)
        self.txt_ss_pass.setText(cfg.password)
        if cfg.driver:
            idx = self.cbo_ss_driver.findText(cfg.driver)
            if idx >= 0:
                self.cbo_ss_driver.setCurrentIndex(idx)

        cfg = self._cm.mysql
        self.txt_my_host.setText(cfg.host)
        self.spn_my_port.setValue(cfg.port)
        self.txt_my_database.setText(cfg.database)
        self.txt_my_user.setText(cfg.username)
        self.txt_my_pass.setText(cfg.password)

        self._recargar_lista_configs()
        self._cargar_config_en_formulario(self._cm.impresora_activa)

    def _probar_sqlserver(self):
        config = self._get_sqlserver_config()
        from database.sqlserver import SQLServerConnection
        conn = SQLServerConnection(config)
        ok, err = conn.test_connection()
        if ok:
            self.lbl_ss_estado.setStyleSheet('color: green;')
            self.lbl_ss_estado.setText(
                f'Conexión exitosa con {conn._driver or "driver detectado"}.'
            )
        else:
            self.lbl_ss_estado.setStyleSheet('color: red;')
            if 'no encontrado' in err or 'No hay drivers' in err:
                err = (
                    'Driver ODBC no instalado.\n'
                    f'Haga clic en "Instalar Driver" o descargue desde:\n'
                    f'{get_driver_download_url()}'
                )
            self.lbl_ss_estado.setText(f'Error: {err}')

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
        config = self._get_mysql_config()
        from database.mysql import MySQLConnection
        conn = MySQLConnection(config)
        ok, err = conn.test_connection()
        if ok:
            self.lbl_my_estado.setStyleSheet('color: green;')
            self.lbl_my_estado.setText('Conexión exitosa.')
        else:
            self.lbl_my_estado.setStyleSheet('color: red;')
            self.lbl_my_estado.setText(f'Error: {err}')

    def _get_sqlserver_config(self) -> ConfigSQLServer:
        driver = self.cbo_ss_driver.currentText()
        if driver == 'Automático (detectar)':
            driver = ''
        return ConfigSQLServer(
            server=self.txt_ss_server.text().strip(),
            database=self.txt_ss_database.text().strip(),
            username=self.txt_ss_user.text().strip(),
            password=self.txt_ss_pass.text().strip(),
            trusted=self.chk_ss_trusted.isChecked(),
            driver=driver,
        )

    def _poblar_drivers_sqlserver(self):
        self.cbo_ss_driver.clear()
        self.cbo_ss_driver.addItem('Automático (detectar)')
        for d in get_available_drivers():
            self.cbo_ss_driver.addItem(d)
        self.cbo_ss_driver.setCurrentIndex(0)

    def _get_mysql_config(self) -> ConfigMySQL:
        return ConfigMySQL(
            host=self.txt_my_host.text().strip(),
            port=self.spn_my_port.value(),
            database=self.txt_my_database.text().strip(),
            username=self.txt_my_user.text().strip(),
            password=self.txt_my_pass.text().strip(),
        )

    def _get_printer_config(self) -> ConfigImpresoras:
        return ConfigImpresoras(
            impresora_remitos=self.cbo_imp_remitos.currentText().strip(),
            tamanio_papel_remitos=self.cbo_papel_remitos.currentText(),
            orientacion_remitos=self.cbo_orientacion_remitos.currentText(),
            copias_remitos=self.spn_copias_remitos.value(),
            bandeja_remitos=self.cbo_bandeja_remitos.currentText().strip(),
            margen_superior_remitos=self.spn_margen_sup.value(),
            margen_inferior_remitos=self.spn_margen_inf.value(),
            margen_izquierdo_remitos=self.spn_margen_izq.value(),
            margen_derecho_remitos=self.spn_margen_der.value(),
            impresora_etiquetas=self.cbo_imp_etiquetas.currentText().strip(),
            tipo_etiqueta=self.cbo_tipo_etiqueta.currentText().strip(),
            ancho_etiqueta=self.spn_ancho_etiqueta.value(),
            alto_etiqueta=self.spn_alto_etiqueta.value(),
            columnas_etiqueta=self.spn_columnas_etiqueta.value(),
            filas_etiqueta=self.spn_filas_etiqueta.value(),
            tamanio_papel_etiquetas=self.cbo_papel_etiquetas.currentText(),
            bandeja_etiquetas=self.cbo_bandeja_etiquetas.currentText().strip(),
            margen_superior_etiquetas=self.spn_etq_m_sup.value(),
            margen_inferior_etiquetas=self.spn_etq_m_inf.value(),
            margen_izquierdo_etiquetas=self.spn_etq_m_izq.value(),
            margen_derecho_etiquetas=self.spn_etq_m_der.value(),
            separacion_etiquetas=self.spn_etq_sep.value(),
            scanner=self.cbo_scanner.currentText().strip(),
            impresora_etiquetas_mateti=self.cbo_imp_etq_mateti.currentText().strip(),
            ancho_etiqueta_mateti=self.spn_ancho_etq_mateti.value(),
            alto_etiqueta_mateti=self.spn_alto_etq_mateti.value(),
            columnas_etiqueta_mateti=self.spn_columnas_etq_mateti.value(),
            separacion_etiqueta_mateti=self.spn_sep_etq_mateti.value(),
            margen_superior_etiquetas_mateti=self.spn_mateti_m_sup.value(),
            margen_inferior_etiquetas_mateti=self.spn_mateti_m_inf.value(),
            margen_izquierdo_etiquetas_mateti=self.spn_mateti_m_izq.value(),
            margen_derecho_etiquetas_mateti=self.spn_mateti_m_der.value(),
        )

    def _guardar(self):
        self._cm.save_sqlserver_config(self._get_sqlserver_config())
        self._cm.save_mysql_config(self._get_mysql_config())
        self._cm.save_printer_config(self._get_printer_config())
        QMessageBox.information(self, 'Configuración', 'Configuración guardada correctamente.')
        self.accept()
