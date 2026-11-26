from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QMessageBox,
    QFormLayout, QPlainTextEdit, QDoubleSpinBox, QTabWidget, QWidget,
)
from config.config_manager import ConfigManager
from database.conexiones import ConfigImpresion


class ConfigImpresionDialog(QDialog):
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self._cm = config_manager
        self.setWindowTitle('Configuración de Impresiones')
        self.setMinimumSize(500, 350)
        self._setup_ui()
        self._cargar_datos()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self._crear_tab_remitente()
        self._crear_tab_numeracion()
        self._crear_tab_valor_declarado()
        self._crear_tab_excluidas()

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.btn_guardar = QPushButton('Guardar')
        self.btn_guardar.setObjectName('btnSuccess')
        self.btn_guardar.clicked.connect(self._guardar)
        buttons.addWidget(self.btn_guardar)
        self.btn_cancelar = QPushButton('Cancelar')
        self.btn_cancelar.setObjectName('btnSecondary')
        self.btn_cancelar.clicked.connect(self.reject)
        buttons.addWidget(self.btn_cancelar)
        layout.addLayout(buttons)

    def _crear_tab_remitente(self):
        tab = QWidget()
        fl = QFormLayout(tab)
        fl.setSpacing(10)
        fl.setContentsMargins(20, 20, 20, 20)

        self.txt_remitente_nombre = QLineEdit()
        self.txt_remitente_nombre.setPlaceholderText('Razón social del remitente')
        fl.addRow('Nombre:', self.txt_remitente_nombre)

        self.txt_remitente_direccion = QLineEdit()
        self.txt_remitente_direccion.setPlaceholderText('Dirección')
        fl.addRow('Dirección:', self.txt_remitente_direccion)

        self.txt_remitente_ciudad = QLineEdit()
        self.txt_remitente_ciudad.setPlaceholderText('Ciudad')
        fl.addRow('Ciudad:', self.txt_remitente_ciudad)

        self.txt_remitente_cuit = QLineEdit()
        self.txt_remitente_cuit.setPlaceholderText('XX-XXXXXXXX-X')
        fl.addRow('CUIT:', self.txt_remitente_cuit)

        self.txt_remitente_telefono = QLineEdit()
        self.txt_remitente_telefono.setPlaceholderText('Teléfono')
        fl.addRow('Teléfono:', self.txt_remitente_telefono)

        self.tabs.addTab(tab, 'Datos del Remitente')

    def _crear_tab_numeracion(self):
        tab = QWidget()
        fl = QFormLayout(tab)
        fl.setSpacing(10)
        fl.setContentsMargins(20, 20, 20, 20)

        self.txt_punto_venta = QLineEdit()
        self.txt_punto_venta.setPlaceholderText('00002')
        self.txt_punto_venta.setMaxLength(5)
        self.txt_punto_venta.setValidator(QRegExpValidator(QRegExp(r'^\d{0,5}$')))
        fl.addRow('Punto de venta:', self.txt_punto_venta)

        self.spn_prox_numero = QSpinBox()
        self.spn_prox_numero.setRange(1, 99999999)
        fl.addRow('Próximo número:', self.spn_prox_numero)

        self.tabs.addTab(tab, 'Numeración de Remitos')

    def _crear_tab_valor_declarado(self):
        tab = QWidget()
        fl = QFormLayout(tab)
        fl.setSpacing(10)
        fl.setContentsMargins(20, 20, 20, 20)

        lbl_info = QLabel(
            'Valor unitario declarado para el cálculo de mercadería.\n'
            'Se utilizará para el remito como referencia del valor de la mercadería.'
        )
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet('color: #555;')
        fl.addRow(lbl_info)

        self.spn_importe_valor_declarado = QDoubleSpinBox()
        self.spn_importe_valor_declarado.setRange(0.0, 9999999.99)
        self.spn_importe_valor_declarado.setDecimals(2)
        self.spn_importe_valor_declarado.setSingleStep(0.01)
        self.spn_importe_valor_declarado.setPrefix('$ ')
        fl.addRow('Importe unitario:', self.spn_importe_valor_declarado)

        self.tabs.addTab(tab, 'Valor Declarado')

    def _crear_tab_excluidas(self):
        tab = QWidget()
        vl = QVBoxLayout(tab)
        vl.setContentsMargins(20, 20, 20, 20)

        lbl_excl = QLabel(
            'Sucursales destino que NO generarán remitos ni etiquetas.\n'
            'Ingrese una por línea (código de sucursal).'
        )
        lbl_excl.setWordWrap(True)
        vl.addWidget(lbl_excl)

        self.txt_sucursales_excluidas = QPlainTextEdit()
        self.txt_sucursales_excluidas.setPlaceholderText('SUC001\nSUC002')
        self.txt_sucursales_excluidas.setMinimumHeight(100)
        vl.addWidget(self.txt_sucursales_excluidas)

        self.tabs.addTab(tab, 'Sucursales Excluidas')

    def _cargar_datos(self):
        cfg = self._cm.impresion
        self.txt_remitente_nombre.setText(cfg.remitente_nombre)
        self.txt_remitente_direccion.setText(cfg.remitente_direccion)
        self.txt_remitente_ciudad.setText(cfg.remitente_ciudad)
        self.txt_remitente_cuit.setText(cfg.remitente_cuit)
        self.txt_remitente_telefono.setText(cfg.remitente_telefono)
        self.txt_punto_venta.setText(cfg.punto_venta)
        self.spn_prox_numero.setValue(cfg.prox_numero_remito)
        self.spn_importe_valor_declarado.setValue(cfg.importe_unitario_valor_declarado)
        self.txt_sucursales_excluidas.setPlainText(cfg.sucursales_excluidas)

    def _get_config(self) -> ConfigImpresion:
        return ConfigImpresion(
            remitente_nombre=self.txt_remitente_nombre.text().strip(),
            remitente_direccion=self.txt_remitente_direccion.text().strip(),
            remitente_ciudad=self.txt_remitente_ciudad.text().strip(),
            remitente_cuit=self.txt_remitente_cuit.text().strip(),
            remitente_telefono=self.txt_remitente_telefono.text().strip(),
            punto_venta=self.txt_punto_venta.text().strip(),
            prox_numero_remito=self.spn_prox_numero.value(),
            sucursales_excluidas=self.txt_sucursales_excluidas.toPlainText().strip(),
            importe_unitario_valor_declarado=self.spn_importe_valor_declarado.value(),
        )

    def _guardar(self):
        self._cm.save_impresion_config(self._get_config())
        QMessageBox.information(self, 'Configuración', 'Configuración de impresiones guardada.')
        self.accept()
