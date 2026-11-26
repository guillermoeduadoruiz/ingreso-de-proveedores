from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QSpinBox, QMessageBox, QAbstractItemView,
)
from PyQt5.QtCore import Qt
from database.sqlserver import SQLServerConnection
from servicios.impresion_svc import ImpresionService


class MatetiWidget(QWidget):
    COL_CODIGO = 0
    COL_BARCODE = 1
    COL_DESCRIPCION = 2
    COL_UM = 3
    COL_CANTIDAD = 4
    COLUMNAS = ['Código Material', 'Cód. de Barras', 'Descripción', 'UM', 'Cant. Etiquetas']

    def __init__(self, sqlserver_conn: SQLServerConnection, impresion_svc: ImpresionService):
        super().__init__()
        self._conn = sqlserver_conn
        self._imp_svc = impresion_svc
        self._on_volver_callback = None
        self._setup_ui()

    def set_on_volver(self, callback):
        self._on_volver_callback = callback

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo = QLabel('<h2>MATETI — Etiquetas de Materiales</h2>')
        layout.addWidget(titulo)

        entrada_layout = QHBoxLayout()
        entrada_layout.addWidget(QLabel('Código de Material:'))
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText('Ingrese el código y presione Enter...')
        self.txt_codigo.setMaximumWidth(280)
        self.txt_codigo.returnPressed.connect(self._agregar_material)
        entrada_layout.addWidget(self.txt_codigo)
        self.btn_agregar = QPushButton('Agregar')
        self.btn_agregar.setObjectName('btnPrimary')
        self.btn_agregar.clicked.connect(self._agregar_material)
        entrada_layout.addWidget(self.btn_agregar)
        self.btn_limpiar = QPushButton('Limpiar lista')
        self.btn_limpiar.setObjectName('btnWarning')
        self.btn_limpiar.clicked.connect(self._limpiar_tabla)
        entrada_layout.addWidget(self.btn_limpiar)
        entrada_layout.addStretch()
        layout.addLayout(entrada_layout)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.horizontalHeaderItem(self.COL_CODIGO).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tabla.horizontalHeaderItem(self.COL_BARCODE).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tabla.horizontalHeaderItem(self.COL_DESCRIPCION).setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tabla.horizontalHeaderItem(self.COL_UM).setTextAlignment(Qt.AlignCenter)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(40)
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(self.COL_CODIGO, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_BARCODE, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_DESCRIPCION, QHeaderView.Stretch)
        header.setSectionResizeMode(self.COL_UM, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_CANTIDAD, QHeaderView.Fixed)
        self.tabla.setColumnWidth(self.COL_CANTIDAD, 140)
        layout.addWidget(self.tabla, 1)

        btn_layout = QHBoxLayout()
        self.btn_volver = QPushButton('Volver')
        self.btn_volver.setObjectName('btnSecondary')
        self.btn_volver.clicked.connect(self._volver)
        btn_layout.addWidget(self.btn_volver)
        btn_layout.addStretch()
        self.btn_quitar = QPushButton('Quitar fila')
        self.btn_quitar.setObjectName('btnDanger')
        self.btn_quitar.clicked.connect(self._quitar_fila)
        btn_layout.addWidget(self.btn_quitar)
        self.btn_imprimir = QPushButton('Imprimir etiquetas')
        self.btn_imprimir.setObjectName('btnSuccess')
        self.btn_imprimir.clicked.connect(self._imprimir_etiquetas)
        btn_layout.addWidget(self.btn_imprimir)
        layout.addLayout(btn_layout)

    def _codigo_ya_existe(self, codigo: str) -> bool:
        for row in range(self.tabla.rowCount()):
            item = self.tabla.item(row, self.COL_CODIGO)
            if item and item.text() == codigo:
                return True
        return False

    def _agregar_material(self):
        codigo = self.txt_codigo.text().strip()
        if not codigo:
            return
        if self._codigo_ya_existe(codigo):
            QMessageBox.warning(self, 'Duplicado', f'El material "{codigo}" ya está en la lista.')
            self.txt_codigo.selectAll()
            return
        try:
            material = self._conn.buscar_material_por_codigo(codigo)
        except Exception as e:
            QMessageBox.warning(self, 'Error de conexión', f'No se pudo consultar el material:\n{e}')
            return
        if not material:
            QMessageBox.information(self, 'No encontrado', f'Material "{codigo}" no encontrado.')
            return

        row = self.tabla.rowCount()
        self.tabla.insertRow(row)

        for col, key, align in [
            (self.COL_CODIGO,      'NumMaterial',  Qt.AlignLeft | Qt.AlignVCenter),
            (self.COL_BARCODE,     'EAN',           Qt.AlignLeft | Qt.AlignVCenter),
            (self.COL_DESCRIPCION, 'Descripcion',   Qt.AlignLeft | Qt.AlignVCenter),
            (self.COL_UM,          'CodigoUnidad',  Qt.AlignCenter),
        ]:
            val = str(material.get(key) or '')
            item = QTableWidgetItem(val)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setTextAlignment(align)
            self.tabla.setItem(row, col, item)

        spn = QSpinBox()
        spn.setMinimum(1)
        spn.setMaximum(9999)
        spn.setValue(1)
        spn.setAlignment(Qt.AlignCenter)
        self.tabla.setCellWidget(row, self.COL_CANTIDAD, spn)

        self.txt_codigo.clear()
        self.txt_codigo.setFocus()

    def _quitar_fila(self):
        row = self.tabla.currentRow()
        if row >= 0:
            self.tabla.removeRow(row)

    def _limpiar_tabla(self):
        if self.tabla.rowCount() == 0:
            return
        resp = QMessageBox.question(
            self, 'Limpiar lista',
            '¿Desea eliminar todos los materiales de la lista?',
            QMessageBox.Yes | QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self.tabla.setRowCount(0)

    def _imprimir_etiquetas(self):
        materiales = self.obtener_materiales()
        if not materiales:
            QMessageBox.information(self, 'Sin materiales', 'Agregue al menos un material antes de imprimir.')
            return
        try:
            filepath = self._imp_svc.imprimir_etiquetas_mateti(materiales)
            if not filepath:
                QMessageBox.warning(self, 'Error', 'No se pudo generar el PDF de etiquetas.')
        except Exception as e:
            QMessageBox.warning(self, 'Error al imprimir', str(e))

    def _volver(self):
        if self._on_volver_callback:
            self._on_volver_callback()

    def obtener_materiales(self) -> list[dict]:
        result = []
        for row in range(self.tabla.rowCount()):
            spn = self.tabla.cellWidget(row, self.COL_CANTIDAD)
            result.append({
                'codigo': self.tabla.item(row, self.COL_CODIGO).text(),
                'barcode': self.tabla.item(row, self.COL_BARCODE).text(),
                'descripcion': self.tabla.item(row, self.COL_DESCRIPCION).text(),
                'um': self.tabla.item(row, self.COL_UM).text(),
                'cantidad_etiquetas': spn.value() if spn else 1,
            })
        return result
