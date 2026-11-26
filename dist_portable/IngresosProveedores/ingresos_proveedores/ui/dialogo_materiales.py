from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
)
from PyQt5.QtCore import Qt


class DialogoMateriales(QDialog):
    COLUMNAS = ['Material', 'Material ERP', 'Descripcion', 'Unid. Previstas', 'Recepcionadas']

    def __init__(self, id_recepcion: str, materiales: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Materiales — Recepción {id_recepcion}')
        self.setMinimumSize(750, 500)
        self._materiales = materiales
        self._setup_ui()
        self._cargar_tabla(materiales)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        lbl_titulo = QLabel(f'<h3>Materiales de la Recepción</h3>')
        layout.addWidget(lbl_titulo)

        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel('Filtrar:'))
        self.txt_filtro = QLineEdit()
        self.txt_filtro.setPlaceholderText('Escriba para filtrar por cualquier columna...')
        self.txt_filtro.setClearButtonEnabled(True)
        self.txt_filtro.textChanged.connect(self._filtrar)
        filtro_layout.addWidget(self.txt_filtro, 1)
        layout.addLayout(filtro_layout)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        for c in range(len(self.COLUMNAS)):
            item = self.tabla.horizontalHeaderItem(c)
            if item:
                item.setTextAlignment(Qt.AlignCenter)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setSortingEnabled(True)
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.tabla.setColumnWidth(0, 140)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.tabla, 1)

        self.lbl_totales = QLabel()
        layout.addWidget(self.lbl_totales)

        btn_cerrar = QPushButton('Cerrar')
        btn_cerrar.setObjectName('btnSecondary')
        btn_cerrar.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

    def _cargar_tabla(self, materiales: list[dict]):
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(len(materiales))
        for i, m in enumerate(materiales):
            for col, key in enumerate(['IDMaterial', 'DatosPrivados1', 'Descripcion', 'CantidadPrevista', 'CantidadRecepcionada']):
                val = str(m.get(key, ''))
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if col == 0:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                elif col == 1:
                    item.setTextAlignment(Qt.AlignCenter)
                elif col >= 3:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(i, col, item)
        self.tabla.setSortingEnabled(True)
        self._actualizar_totales(materiales)

    def _actualizar_totales(self, materiales: list[dict]):
        total_previstas = 0
        total_recepcionadas = 0
        materiales_distintos = set()
        for m in materiales:
            try:
                total_previstas += float(m.get('CantidadPrevista', 0) or 0)
            except (ValueError, TypeError):
                pass
            try:
                total_recepcionadas += float(m.get('CantidadRecepcionada', 0) or 0)
            except (ValueError, TypeError):
                pass
            mat = m.get('IDMaterial')
            if mat:
                materiales_distintos.add(mat)
        self.lbl_totales.setText(
            f'<b>Materiales:</b> {len(materiales_distintos)}  |  '
            f'<b>Unid. Previstas:</b> {total_previstas:,.2f}  |  '
            f'<b>Recepcionadas:</b> {total_recepcionadas:,.2f}'
        )

    def _filtrar(self, texto: str):
        texto = texto.strip().lower()
        if not texto:
            self._cargar_tabla(self._materiales)
            return
        filtrados = [
            m for m in self._materiales
            if any(texto in str(m.get(k, '')).lower() for k in ['IDMaterial', 'DatosPrivados1', 'Descripcion', 'CantidadPrevista', 'CantidadRecepcionada'])
        ]
        self._cargar_tabla(filtrados)
