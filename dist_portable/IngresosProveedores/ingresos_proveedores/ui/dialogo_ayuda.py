import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QTextBrowser, QPushButton, QLabel,
    QSplitter,
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont


SECCIONES = [
    ('General', 'general'),
    ('Paso 1 - Selección de Recepciones', 'paso1'),
    ('Paso 2 - Ingreso de Remitos', 'paso2'),
    ('Paso 3 - Confirmación y Registro', 'paso3'),
    ('Consulta de Ingresos', 'consulta'),
    ('Configuración del Sistema', 'configuracion'),
]


class DialogoAyuda(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Manual de Uso')
        self.setMinimumSize(900, 600)
        self._manual_path = self._buscar_manual()
        self._setup_ui()
        if SECCIONES:
            self._navegar_a(SECCIONES[0][1])

    def _buscar_manual(self) -> str:
        from utils.paths import assets_dir
        return os.path.join(assets_dir(), 'manual.html')

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        lbl = QLabel('<h2>Manual de Uso del Sistema</h2>')
        layout.addWidget(lbl)

        splitter = QSplitter(Qt.Horizontal)

        self.lista_secciones = QListWidget()
        self.lista_secciones.setMaximumWidth(280)
        self.lista_secciones.setFont(QFont('', 11))
        for nombre, anchor in SECCIONES:
            item = QListWidgetItem(nombre)
            item.setData(Qt.UserRole, anchor)
            self.lista_secciones.addItem(item)
        self.lista_secciones.currentRowChanged.connect(self._on_seleccion_cambio)
        splitter.addWidget(self.lista_secciones)

        self.visor = QTextBrowser()
        self.visor.setOpenExternalLinks(False)
        splitter.addWidget(self.visor)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        btn_cerrar = QPushButton('Cerrar')
        btn_cerrar.setObjectName('btnSecondary')
        btn_cerrar.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

        if os.path.exists(self._manual_path):
            with open(self._manual_path, 'r', encoding='utf-8') as f:
                self._html_completo = f.read()
        else:
            self._html_completo = '<p>No se encontró el archivo de manual.</p>'

    def _on_seleccion_cambio(self, row):
        if row < 0:
            return
        item = self.lista_secciones.item(row)
        anchor = item.data(Qt.UserRole)
        self._navegar_a(anchor)

    def _navegar_a(self, anchor: str):
        url = f'{self._manual_path}#{anchor}'
        self.visor.setSource(QUrl.fromLocalFile(self._manual_path))
        self.visor.scrollToAnchor(anchor)
