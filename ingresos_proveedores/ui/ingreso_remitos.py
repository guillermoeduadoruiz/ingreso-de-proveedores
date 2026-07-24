from datetime import date
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QMessageBox, QGroupBox, QDateEdit, QSpinBox, QDoubleSpinBox,
)
from PyQt5.QtCore import Qt, QDate, QEvent, QRegExp
from PyQt5.QtGui import QFontMetrics, QRegExpValidator
from modelos.proveedor import Proveedor
from modelos.remito import Remito
from modelos.recepcion import RecepcionPrevista
from servicios.ingreso_svc import IngresoService


class IngresoRemitosWidget(QWidget):
    COL_RECEPCIONES = 4

    def __init__(self, ingreso_svc: IngresoService):
        super().__init__()
        self._ingreso_svc = ingreso_svc
        self._proveedor: Proveedor | None = None
        self._recepciones: list[RecepcionPrevista] = []
        self._remitos: list[Remito] = []
        self._on_continuar_callback = None
        self._on_volver_callback = None
        self._on_agregar_mas_callback = None
        self._expanded_rows: set[int] = set()
        self._default_row_heights: dict[int, int] = {}
        self._rp_info_expanded = False
        self._rp_info_full_text = ''
        self._valor_declarado_unitario: float = 0.0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        titulo = QLabel('<h2>Paso 2: Ingreso de Remitos</h2>')
        layout.addWidget(titulo)

        self.lbl_proveedor_info = QLabel('')
        self.lbl_proveedor_info.setStyleSheet('font-size: 13px; color: #555;')
        layout.addWidget(self.lbl_proveedor_info)

        self.lbl_rp_info = QLabel('')
        self.lbl_rp_info.setStyleSheet('font-size: 12px; color: #2196F3; font-weight: bold;')
        self.lbl_rp_info.setWordWrap(False)
        self.lbl_rp_info.installEventFilter(self)
        layout.addWidget(self.lbl_rp_info)

        fila_fecha_ingreso = QHBoxLayout()
        fila_fecha_ingreso.addWidget(QLabel('Fecha Ingreso al CD:'))
        self.dte_fecha_ingreso = QDateEdit()
        self.dte_fecha_ingreso.setCalendarPopup(True)
        self.dte_fecha_ingreso.setDate(QDate.currentDate())
        self.dte_fecha_ingreso.setMinimumWidth(120)
        fila_fecha_ingreso.addWidget(self.dte_fecha_ingreso)
        fila_fecha_ingreso.addStretch(1)
        layout.addLayout(fila_fecha_ingreso)

        grp_nuevo = QGroupBox('Agregar Remito')
        form_layout = QVBoxLayout(grp_nuevo)

        fila1 = QHBoxLayout()
        fila1.addWidget(QLabel('N° Remito:'))
        self.txt_num_remito = QLineEdit()
        self.txt_num_remito.setPlaceholderText('Ej: 0001-00012345')
        self.txt_num_remito.setValidator(QRegExpValidator(QRegExp(r'^\d{0,5}-?\d{0,20}$')))
        fila1.addWidget(self.txt_num_remito, 1)
        fila1.addWidget(QLabel('Fecha:'))
        self.dte_fecha = QDateEdit()
        self.dte_fecha.setCalendarPopup(True)
        self.dte_fecha.setDate(QDate.currentDate())
        fila1.addWidget(self.dte_fecha)
        form_layout.addLayout(fila1)

        fila2 = QHBoxLayout()
        fila2.addWidget(QLabel('Bultos:'))
        self.spn_bultos = QSpinBox()
        self.spn_bultos.setMinimum(1)
        self.spn_bultos.setMaximum(99999)
        self.spn_bultos.setValue(1)
        self.spn_bultos.setMinimumWidth(80)
        fila2.addWidget(self.spn_bultos)
        fila2.addWidget(QLabel('Unidades:'))
        self.spn_unidades = QSpinBox()
        self.spn_unidades.setMinimum(0)
        self.spn_unidades.setMaximum(99999)
        self.spn_unidades.setValue(0)
        self.spn_unidades.setMinimumWidth(80)
        fila2.addWidget(self.spn_unidades)
        fila2.addWidget(QLabel('Valor Declarado Unit.:'))
        self.spn_valor_unitario = QDoubleSpinBox()
        self.spn_valor_unitario.setPrefix('$ ')
        self.spn_valor_unitario.setDecimals(2)
        self.spn_valor_unitario.setMinimum(0.0)
        self.spn_valor_unitario.setMaximum(99999999.99)
        self.spn_valor_unitario.setSingleStep(0.50)
        self.spn_valor_unitario.setValue(0.0)
        self.spn_valor_unitario.setMinimumWidth(130)
        fila2.addWidget(self.spn_valor_unitario)
        fila2.addStretch(1)
        self.btn_agregar_remito = QPushButton('Agregar Remito')
        self.btn_agregar_remito.setObjectName('btnPrimary')
        fila2.addWidget(self.btn_agregar_remito)
        form_layout.addLayout(fila2)

        self.lbl_valor_declarado = QLabel('')
        self.lbl_valor_declarado.setStyleSheet(
            'font-size: 12px; color: #4CAF50; font-weight: bold; padding: 4px;'
        )
        self.lbl_valor_declarado.setVisible(False)
        form_layout.addWidget(self.lbl_valor_declarado)
        layout.addWidget(grp_nuevo)

        self.tabla_remitos = QTableWidget()
        self.tabla_remitos.setColumnCount(7)
        self.tabla_remitos.setHorizontalHeaderLabels(
            ['N° Remito', 'Fecha', 'Bultos', 'Unidades', 'Valor Declarado', 'Recepciones Asociadas', 'Destino']
        )
        self.tabla_remitos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_remitos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_remitos.setAlternatingRowColors(True)
        self.tabla_remitos.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla_remitos, 1)

        grp_acciones = QGroupBox()
        acc_layout = QHBoxLayout(grp_acciones)
        self.btn_quitar = QPushButton('Quitar Remito')
        self.btn_quitar.setObjectName('btnDanger')
        acc_layout.addWidget(self.btn_quitar)
        acc_layout.addStretch(1)
        self.btn_agregar_mas = QPushButton('Agregar más Remitos')
        self.btn_agregar_mas.setObjectName('btnSecondary')
        self.btn_agregar_mas.setEnabled(False)
        acc_layout.addWidget(self.btn_agregar_mas)
        self.btn_atras = QPushButton('← Volver a Proveedores')
        self.btn_atras.setObjectName('btnSecondary')
        acc_layout.addWidget(self.btn_atras)
        self.btn_continuar = QPushButton('Continuar al Registro →')
        self.btn_continuar.setObjectName('btnSuccess')
        self.btn_continuar.setEnabled(False)
        acc_layout.addWidget(self.btn_continuar)
        layout.addWidget(grp_acciones)

        self._conectar_eventos()

    def _conectar_eventos(self):
        self.btn_agregar_remito.clicked.connect(self._agregar_remito)
        self.btn_quitar.clicked.connect(self._quitar_remito)
        self.btn_continuar.clicked.connect(self._continuar)
        self.btn_atras.clicked.connect(self._volver)
        self.btn_agregar_mas.clicked.connect(self._agregar_mas)
        self.txt_num_remito.returnPressed.connect(self._agregar_remito)
        self.txt_num_remito.editingFinished.connect(self._formatear_remito)
        self.tabla_remitos.cellClicked.connect(self._on_cell_clicked)
        self.spn_unidades.valueChanged.connect(self._actualizar_valor_declarado_label)
        self.spn_valor_unitario.valueChanged.connect(self._actualizar_valor_declarado_label)

    def set_proveedor(self, proveedor: Proveedor, recepciones: list[RecepcionPrevista] | None = None,
                       valor_declarado_unitario: float = 0.0):
        self._proveedor = proveedor
        self._remitos.clear()
        self._recepciones = recepciones or []
        self._valor_declarado_unitario = valor_declarado_unitario
        self.spn_valor_unitario.setValue(valor_declarado_unitario)
        self.lbl_valor_declarado.setVisible(False)
        self._rp_info_expanded = False
        self.lbl_rp_info.setWordWrap(False)
        self.dte_fecha_ingreso.setDate(QDate.currentDate())
        self.lbl_rp_info.setStyleSheet('font-size: 12px; color: #2196F3; font-weight: bold;')
        self.lbl_proveedor_info.setText(
            f'Proveedor: <b>{proveedor.num_proveedor}</b> - {proveedor.descripcion}'
        )
        if self._recepciones:
            destinos = {r.sucursal_destino for r in self._recepciones}
            destino_str = ', '.join(f'{d} ({self._recepciones[0].nombre_destino})' for d in destinos)
            ids = ', '.join(r.id_recepcion for r in self._recepciones)
            self._rp_info_full_text = (
                f'Recepciones Previstas seleccionadas: {ids} — Destino: {destino_str}'
            )
        else:
            self._rp_info_full_text = 'Sin recepciones previstas seleccionadas.'
        fm = self.lbl_rp_info.fontMetrics()
        self.lbl_rp_info.setText(
            fm.elidedText(self._rp_info_full_text, Qt.ElideRight, self.lbl_rp_info.width())
        )
        self._cargar_tabla()
        self._actualizar_botones()

    def _agregar_remito(self):
        if not self._proveedor:
            return

        num_remito = self.txt_num_remito.text().strip()
        if not num_remito:
            QMessageBox.warning(self, 'Validación', 'El número de remito es obligatorio.')
            self.txt_num_remito.setFocus()
            return

        if not QRegExp(r'^\d{4,5}-\d{1,20}$').exactMatch(num_remito):
            QMessageBox.warning(
                self, 'Formato inválido',
                'El número de remito debe tener el formato: PPPP-NNNNN\n'
                'Ejemplo: 0001-00012345'
            )
            self.txt_num_remito.setFocus()
            self.txt_num_remito.selectAll()
            return

        try:
            if self._ingreso_svc.remito_ya_registrado(num_remito, self._proveedor.num_proveedor):
                QMessageBox.warning(
                    self, 'Remito Duplicado',
                    f'El remito N° {num_remito} ya fue registrado para el proveedor '
                    f'{self._proveedor.num_proveedor}.'
                )
                self.txt_num_remito.setFocus()
                self.txt_num_remito.selectAll()
                return
        except Exception:
            pass

        for r in self._remitos:
            if r.num_remito == num_remito:
                QMessageBox.warning(
                    self, 'Remito Duplicado',
                    f'El remito N° {num_remito} ya fue agregado en esta sesión.'
                )
                self.txt_num_remito.setFocus()
                self.txt_num_remito.selectAll()
                return

        fecha_remito = self.dte_fecha.date().toPyDate()
        if fecha_remito > date.today():
            QMessageBox.warning(self, 'Validación', 'La fecha del remito no puede ser futura.')
            self.dte_fecha.setFocus()
            return

        fecha_ingreso_cd = self.dte_fecha_ingreso.date().toPyDate()
        if fecha_ingreso_cd > date.today():
            QMessageBox.warning(self, 'Validación', 'La fecha de ingreso al CD no puede ser futura.')
            self.dte_fecha_ingreso.setFocus()
            return

        cantidad_bultos = self.spn_bultos.value()
        cantidad_unidades = self.spn_unidades.value()
        valor_unitario = self.spn_valor_unitario.value()

        remito = Remito(
            num_remito=num_remito,
            fecha_remito=fecha_remito,
            cantidad_bultos=cantidad_bultos,
            cantidad_unidades=cantidad_unidades,
            valor_declarado_unitario=valor_unitario,
            recepciones=self._recepciones[:],
        )
        self._remitos.append(remito)
        self._cargar_tabla()

        self.txt_num_remito.clear()
        self.spn_bultos.setValue(1)
        self.spn_unidades.setValue(0)
        self.dte_fecha.setDate(QDate.currentDate())
        self.lbl_valor_declarado.setVisible(False)
        self.txt_num_remito.setFocus()
        self._actualizar_botones()

    def _formatear_remito(self):
        texto = self.txt_num_remito.text().strip()
        solo_digitos = ''.join(c for c in texto if c.isdigit())
        if not solo_digitos:
            return
        if len(solo_digitos) <= 4:
            self.txt_num_remito.setText(solo_digitos)
        else:
            self.txt_num_remito.setText(f'{solo_digitos[:4]}-{solo_digitos[4:]}')

    def _actualizar_valor_declarado_label(self):
        unidades = self.spn_unidades.value()
        valor_unit = self.spn_valor_unitario.value()
        if unidades > 0 and valor_unit > 0:
            total = unidades * valor_unit
            self.lbl_valor_declarado.setText(
                f'Valor Declarado: {unidades} x ${valor_unit:,.2f} = ${total:,.2f}'
            )
            self.lbl_valor_declarado.setVisible(True)
        else:
            self.lbl_valor_declarado.setVisible(False)

    def _quitar_remito(self):
        row = self.tabla_remitos.currentRow()
        if 0 <= row < len(self._remitos):
            self._remitos.pop(row)
            self._cargar_tabla()
            self._actualizar_botones()

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
            receps = ', '.join(f'{rp.id_recepcion} ({rp.descripcion_clase})' for rp in r.recepciones)
            self.tabla_remitos.setItem(i, 5, QTableWidgetItem(receps))
            destino = r.recepciones[0].nombre_destino if r.recepciones else ''
            self.tabla_remitos.setItem(i, 6, QTableWidgetItem(destino))
        header = self.tabla_remitos.horizontalHeader()
        for c in range(self.tabla_remitos.columnCount()):
            if c == 5:
                header.setSectionResizeMode(c, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(c, QHeaderView.ResizeToContents)

    def eventFilter(self, obj, event):
        if obj is self.lbl_rp_info and event.type() == QEvent.MouseButtonPress:
            if self.lbl_rp_info.text():
                self._toggle_rp_info()
            return True
        return super().eventFilter(obj, event)

    def _toggle_rp_info(self):
        self._rp_info_expanded = not self._rp_info_expanded
        if self._rp_info_expanded:
            self.lbl_rp_info.setWordWrap(True)
            self.lbl_rp_info.setText(self._rp_info_full_text)
            self.lbl_rp_info.setStyleSheet(
                'font-size: 12px; color: #2196F3; font-weight: bold; '
                'border: 1px solid #2196F3; padding: 4px;'
            )
        else:
            self.lbl_rp_info.setWordWrap(False)
            fm = self.lbl_rp_info.fontMetrics()
            self.lbl_rp_info.setText(
                fm.elidedText(self._rp_info_full_text, Qt.ElideRight, self.lbl_rp_info.width())
            )
            self.lbl_rp_info.setStyleSheet('font-size: 12px; color: #2196F3; font-weight: bold;')

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

    def _actualizar_botones(self):
        tiene_remitos = len(self._remitos) > 0
        self.btn_continuar.setEnabled(tiene_remitos)
        self.btn_agregar_mas.setEnabled(tiene_remitos)

    def _continuar(self):
        if not self._on_continuar_callback or len(self._remitos) == 0:
            return
        fecha_ingreso_cd = self.dte_fecha_ingreso.date().toPyDate()
        if fecha_ingreso_cd > date.today():
            QMessageBox.warning(self, 'Validación', 'La fecha de ingreso al CD no puede ser futura.')
            self.dte_fecha_ingreso.setFocus()
            return
        self._on_continuar_callback(self._remitos, fecha_ingreso_cd)

    def _volver(self):
        if self._on_volver_callback:
            self._on_volver_callback()

    def _agregar_mas(self):
        if self._on_agregar_mas_callback:
            self._on_agregar_mas_callback(self._proveedor, self._remitos)

    def set_on_continuar(self, callback):
        self._on_continuar_callback = callback

    def set_on_volver(self, callback):
        self._on_volver_callback = callback

    def set_on_agregar_mas(self, callback):
        self._on_agregar_mas_callback = callback

    def restaurar_remitos(self, remitos: list[Remito]):
        self._remitos = remitos[:]
        self._cargar_tabla()
        self._actualizar_botones()

    @property
    def remitos(self) -> list[Remito]:
        return self._remitos

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._rp_info_expanded and self._rp_info_full_text:
            fm = self.lbl_rp_info.fontMetrics()
            self.lbl_rp_info.setText(
                fm.elidedText(self._rp_info_full_text, Qt.ElideRight, self.lbl_rp_info.width())
            )

    @property
    def proveedor(self) -> Proveedor | None:
        return self._proveedor
