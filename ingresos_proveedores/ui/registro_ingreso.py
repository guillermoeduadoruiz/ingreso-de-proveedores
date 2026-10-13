from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QMessageBox,
    QGroupBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics
from modelos.proveedor import Proveedor
from modelos.remito import Remito
from modelos.ingreso import Ingreso
from servicios.ingreso_svc import IngresoService
from servicios.impresion_svc import ImpresionService
from datetime import date


class RegistroIngresoWidget(QWidget):
    COL_RECEPCIONES = 4

    def __init__(self, ingreso_svc: IngresoService, impresion_svc: ImpresionService | None = None):
        super().__init__()
        self._svc = ingreso_svc
        self._imp_svc = impresion_svc
        self._proveedor: Proveedor | None = None
        self._remitos: list[Remito] = []
        self._on_finalizar_callback = None
        self._on_cancelar_callback = None
        self._registrando = False
        self._expanded_rows: set[int] = set()
        self._default_row_heights: dict[int, int] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        titulo = QLabel('<h2>Paso 3: Confirmar Ingreso de Mercadería</h2>')
        layout.addWidget(titulo)

        grp_resumen = QGroupBox('Resumen del Ingreso')
        res_layout = QVBoxLayout(grp_resumen)

        self.lbl_id = QLabel('')
        self.lbl_id.setStyleSheet('font-size: 16px; font-weight: bold; color: #2196F3;')
        res_layout.addWidget(self.lbl_id)

        self.lbl_fecha = QLabel('')
        res_layout.addWidget(self.lbl_fecha)

        self.lbl_proveedor = QLabel('')
        self.lbl_proveedor.setStyleSheet('font-size: 13px;')
        res_layout.addWidget(self.lbl_proveedor)

        layout.addWidget(grp_resumen)

        grp_remitos = QGroupBox('Remitos Asociados')
        rem_layout = QVBoxLayout(grp_remitos)

        self.tabla_remitos = QTableWidget()
        self.tabla_remitos.setColumnCount(7)
        self.tabla_remitos.setHorizontalHeaderLabels(
            ['N° Remito', 'Fecha', 'Bultos', 'Unidades', 'Valor Declarado', 'Recepciones Previstas', 'Destino']
        )
        self.tabla_remitos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_remitos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_remitos.setAlternatingRowColors(True)
        self.tabla_remitos.verticalHeader().setVisible(False)
        rem_layout.addWidget(self.tabla_remitos, 1)

        layout.addWidget(grp_remitos, 1)

        grp_acciones = QGroupBox()
        acc_layout = QHBoxLayout(grp_acciones)
        self.btn_cancelar = QPushButton('← Modificar Datos')
        self.btn_cancelar.setObjectName('btnSecondary')
        acc_layout.addWidget(self.btn_cancelar)
        acc_layout.addStretch(1)
        self.btn_confirmar = QPushButton('Confirmar y Registrar')
        self.btn_confirmar.setObjectName('btnSuccess')
        self.btn_confirmar.setMinimumWidth(200)
        acc_layout.addWidget(self.btn_confirmar)
        layout.addWidget(grp_acciones)

        self.btn_cancelar.clicked.connect(self._cancelar)
        self.btn_confirmar.clicked.connect(self._confirmar)
        self.tabla_remitos.cellClicked.connect(self._on_cell_clicked)

    def set_datos(self, proveedor: Proveedor, remitos: list[Remito], fecha_ingreso_cd=None):
        self._registrando = False
        self._proveedor = proveedor
        self._remitos = remitos
        self._fecha_ingreso_cd = fecha_ingreso_cd or date.today()
        self._id_ingreso_tmp = None

        self.lbl_id.setText('ID de Ingreso: Por generar al confirmar')
        self.lbl_id.setStyleSheet('font-size: 16px; font-weight: bold; color: #2196F3;')
        self.lbl_fecha.setText(f'Fecha de Ingreso: {self._fecha_ingreso_cd.strftime("%d/%m/%Y")}')
        self.lbl_proveedor.setText(
            f'Proveedor: {proveedor.num_proveedor} - {proveedor.descripcion}'
        )
        self.btn_confirmar.setEnabled(True)
        self.btn_cancelar.setText('← Modificar Datos')
        self._cargar_tabla()

    def _cargar_tabla(self):
        self._expanded_rows.clear()
        self._default_row_heights.clear()
        self.tabla_remitos.setRowCount(len(self._remitos))
        for i, r in enumerate(self._remitos):
            self.tabla_remitos.setItem(i, 0, QTableWidgetItem(r.num_remito))
            self.tabla_remitos.setItem(i, 1, QTableWidgetItem(r.fecha_remito.strftime('%d/%m/%Y')))
            self.tabla_remitos.setItem(i, 2, QTableWidgetItem(str(r.cantidad_bultos)))
            self.tabla_remitos.setItem(i, 3, QTableWidgetItem(str(r.cantidad_unidades)))
            total_vd = r.valor_declarado_total
            item_vd = QTableWidgetItem(f'${total_vd:,.2f}' if total_vd > 0 else '-')
            item_vd.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabla_remitos.setItem(i, 4, item_vd)
            receps = ', '.join(
                f'{rp.id_recepcion} ({rp.descripcion_clase})'
                for rp in r.recepciones
            )
            self.tabla_remitos.setItem(i, 5, QTableWidgetItem(receps))
            destino = r.recepciones[0].nombre_destino if r.recepciones else ''
            self.tabla_remitos.setItem(i, 6, QTableWidgetItem(destino))
        header = self.tabla_remitos.horizontalHeader()
        for c in range(self.tabla_remitos.columnCount()):
            if c == 5:
                header.setSectionResizeMode(c, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(c, QHeaderView.ResizeToContents)

    def _on_cell_clicked(self, row, col):
        if col != self.COL_RECEPCIONES:
            return
        if row < 0 or row >= len(self._remitos):
            return
        if row in self._expanded_rows:
            altura_orig = self._default_row_heights.pop(row, 25)
            self.tabla_remitos.setRowHeight(row, altura_orig)
            self._expanded_rows.discard(row)
        else:
            if row not in self._default_row_heights:
                self._default_row_heights[row] = self.tabla_remitos.rowHeight(row)
            item = self.tabla_remitos.item(row, self.COL_RECEPCIONES)
            if not item:
                return
            ancho = self.tabla_remitos.columnWidth(self.COL_RECEPCIONES) - 10
            fm = QFontMetrics(self.tabla_remitos.font())
            rect = fm.boundingRect(0, 0, ancho, 0, Qt.AlignLeft | Qt.TextWordWrap, item.text())
            self.tabla_remitos.setRowHeight(row, rect.height() + 10)
            self._expanded_rows.add(row)

    def _confirmar(self):
        if self._registrando:
            return
        if not self._proveedor or not self._remitos:
            QMessageBox.warning(
                self, 'Sin datos',
                'No hay datos de ingreso para confirmar.\n'
                'Vuelva al paso anterior y verifique la información.'
            )
            return

        self._registrando = True
        self.btn_confirmar.setEnabled(False)

        total_bultos = sum(r.cantidad_bultos for r in self._remitos)
        msg = (
            f'Confirma el ingreso de mercadería?\n\n'
            f'Proveedor: {self._proveedor.num_proveedor} - {self._proveedor.descripcion}\n'
            f'Remitos: {len(self._remitos)}\n'
            f'Total bultos: {total_bultos}'
        )
        reply = QMessageBox.question(
            self, 'Confirmar Ingreso', msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            self._registrando = False
            self.btn_confirmar.setEnabled(True)
            return

        try:
            ingreso = self._svc.registrar(self._proveedor, self._remitos, self._fecha_ingreso_cd)
            self.lbl_id.setText(f'ID de Ingreso: {ingreso.id_ingreso}')
            self.lbl_id.setStyleSheet(
                'font-size: 16px; font-weight: bold; color: #4CAF50;'
            )

            self._imprimir_documentos(ingreso)

            QMessageBox.information(
                self, 'Ingreso Registrado',
                f'Ingreso registrado exitosamente.\n\n'
                f'ID de Ingreso: {ingreso.id_ingreso}\n'
                f'Fecha: {ingreso.fecha_ingreso.strftime("%d/%m/%Y")}\n'
                f'Remitos: {len(ingreso.remitos)}\n'
                f'Proveedor: {ingreso.proveedor.num_proveedor}'
            )

            self.btn_confirmar.setEnabled(False)
            self.btn_cancelar.setText('← Nuevo Ingreso')

            if self._on_finalizar_callback:
                self._on_finalizar_callback(ingreso)

        except Exception as e:
            self._registrando = False
            self.btn_confirmar.setEnabled(True)
            QMessageBox.critical(
                self, 'Error',
                f'Error al registrar el ingreso:\n{e}'
            )

    def _imprimir_documentos(self, ingreso: Ingreso):
        if self._imp_svc is None:
            return
        exitos, errores = self._imp_svc.imprimir_documentos(ingreso)
        if errores:
            QMessageBox.warning(
                self, 'Impresión',
                'No se pudieron generar:\n' + '\n'.join(errores)
            )
        elif exitos:
            QMessageBox.information(
                self, 'Impresión',
                'Documentos generados:\n' + '\n'.join(exitos)
            )

    def _cancelar(self):
        if self._on_cancelar_callback:
            self._on_cancelar_callback()

    def set_on_finalizar(self, callback):
        self._on_finalizar_callback = callback

    def set_on_cancelar(self, callback):
        self._on_cancelar_callback = callback
