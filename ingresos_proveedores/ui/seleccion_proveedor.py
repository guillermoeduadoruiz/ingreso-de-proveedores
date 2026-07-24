from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView,
    QMessageBox, QGroupBox, QComboBox, QAbstractItemView,
    QSizePolicy, QApplication, QStyle,
)
from PyQt5.QtCore import Qt, QEvent
from modelos.recepcion import RecepcionPrevista
from servicios.recepcion_svc import RecepcionService
from ui.dialogo_materiales import DialogoMateriales


class SeleccionProveedorWidget(QWidget):
    COL_RP = [
        'Sel', 'IDRecepcion', 'Clase', 'Fecha Prevista',
        'Proveedor', 'Razon Social',
        'Sucursal Destino', 'Nombre Destino', 'Ver',
    ]

    HEADER_ALIGN = Qt.AlignCenter

    OPCIONES_DIAS = [
        ('Ultimos 30 días', 30),
        ('Ultimos 60 días', 60),
        ('Ultimos 90 días', 90),
        ('Ultimos 180 días', 180),
        ('Ultimos 365 días', 365),
    ]

    COL_FILTRO = {2: 'Clase', 5: 'Razon Social', 6: 'Sucursal Destino', 7: 'Nombre Destino'}

    def __init__(self, recepcion_svc: RecepcionService):
        super().__init__()
        self._svc_recepcion = recepcion_svc
        self._recepciones_todas: list[RecepcionPrevista] = []
        self._recepciones: list[RecepcionPrevista] = []
        self._recepciones_seleccionadas: list[RecepcionPrevista] = []
        self._on_confirmar_callback = None
        self._on_volver_sin_cambios_callback = None
        self._filtros = {2: '', 5: '', 6: '', 7: ''}
        self._label_expanded = False
        self._resumen_full_text = ''
        self._prefiltro_activo = False
        self._prefiltro_id_proveedor = ''
        self._prefiltro_nombre_destino = ''
        self._recepciones_asociadas_ids: set[str] = set()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        self.titulo_lbl = QLabel('<h2>Paso 1: Seleccionar Recepciones Previstas</h2>')
        layout.addWidget(self.titulo_lbl)

        filtro_layout = QHBoxLayout()
        filtro_layout.addWidget(QLabel('Buscar RP:'))
        self.txt_filtro = QLineEdit()
        self.txt_filtro.setPlaceholderText('ID Recepción, código de proveedor o razón social (separar múltiples RP con espacio)')
        self.txt_filtro.setMinimumWidth(300)
        self.btn_buscar = QPushButton('Buscar')
        self.btn_buscar.setObjectName('btnPrimary')
        self.btn_limpiar = QPushButton('Limpiar')
        filtro_layout.addWidget(self.txt_filtro, 1)
        filtro_layout.addWidget(self.btn_buscar)
        filtro_layout.addWidget(self.btn_limpiar)
        filtro_layout.addSpacing(20)
        filtro_layout.addWidget(QLabel('Fecha:'))
        self.cbo_dias = QComboBox()
        for label, _ in self.OPCIONES_DIAS:
            self.cbo_dias.addItem(label)
        self.cbo_dias.setCurrentIndex(len(self.OPCIONES_DIAS) - 1)
        filtro_layout.addWidget(self.cbo_dias)
        layout.addLayout(filtro_layout)

        self.tabla_rp = QTableWidget()
        self.tabla_rp.setColumnCount(len(self.COL_RP))
        self.tabla_rp.setHorizontalHeaderLabels(self.COL_RP)
        for c in range(len(self.COL_RP)):
            item = self.tabla_rp.horizontalHeaderItem(c)
            if item:
                item.setTextAlignment(self.HEADER_ALIGN)
        self.tabla_rp.horizontalHeader().setStretchLastSection(True)
        self.tabla_rp.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_rp.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla_rp.setAlternatingRowColors(True)
        self.tabla_rp.verticalHeader().setVisible(False)
        layout.addWidget(self.tabla_rp, 1)

        self.grp_resumen_seleccion = QGroupBox('Resumen de Selección')
        resumen_layout = QHBoxLayout(self.grp_resumen_seleccion)
        self.lbl_resumen_recepciones = QLabel('Recepciones: 0')
        self.lbl_resumen_destinos = QLabel('Destinos: 0')
        self.lbl_resumen_skus = QLabel('SKU: 0')
        self.lbl_resumen_previstas = QLabel('Previstas: 0')
        self.lbl_resumen_recepcionadas = QLabel('Recepcionadas: 0')
        for lbl in (self.lbl_resumen_recepciones, self.lbl_resumen_destinos, self.lbl_resumen_skus, self.lbl_resumen_previstas, self.lbl_resumen_recepcionadas):
            lbl.setStyleSheet('font-size: 12px; font-weight: bold;')
            resumen_layout.addWidget(lbl)
            resumen_layout.addSpacing(20)
        self.grp_resumen_seleccion.setVisible(False)
        layout.addWidget(self.grp_resumen_seleccion)

        grp_accion = QGroupBox()
        acc_layout = QHBoxLayout(grp_accion)
        self.lbl_resumen = QLabel('Ninguna recepción seleccionada.')
        self.lbl_resumen.setStyleSheet('font-weight: bold; color: #2196F3; font-size: 13px;')
        self.lbl_resumen.setWordWrap(False)
        self.lbl_resumen.installEventFilter(self)
        acc_layout.addWidget(self.lbl_resumen, 1)
        self.btn_confirmar = QPushButton('Confirmar y Continuar →')
        self.btn_confirmar.setObjectName('btnSuccess')
        self.btn_confirmar.setEnabled(False)
        self.btn_confirmar.setMinimumWidth(200)
        acc_layout.addWidget(self.btn_confirmar)
        self.btn_volver_sin_cambios = QPushButton('← Volver a Remitos')
        self.btn_volver_sin_cambios.setObjectName('btnSecondary')
        self.btn_volver_sin_cambios.setVisible(False)
        self.btn_volver_sin_cambios.clicked.connect(self._volver_sin_cambios)
        acc_layout.addWidget(self.btn_volver_sin_cambios)
        layout.addWidget(grp_accion)

        self.btn_buscar.clicked.connect(self._buscar)
        self.btn_limpiar.clicked.connect(self._limpiar)
        self.txt_filtro.returnPressed.connect(self._buscar)
        self.cbo_dias.currentIndexChanged.connect(self._buscar)
        self.tabla_rp.cellClicked.connect(self._on_cell_clicked)
        self.btn_confirmar.clicked.connect(self._confirmar)

    def set_on_confirmar(self, callback):
        self._on_confirmar_callback = callback

    def set_on_volver_sin_cambios(self, callback):
        self._on_volver_sin_cambios_callback = callback

    def _volver_sin_cambios(self):
        if self._on_volver_sin_cambios_callback:
            self._on_volver_sin_cambios_callback()

    def set_prefiltro(self, id_proveedor: str, nombre_destino: str, remitos_asociados: list = None):
        self._prefiltro_activo = True
        self._prefiltro_id_proveedor = id_proveedor
        self._prefiltro_nombre_destino = nombre_destino
        self._recepciones_asociadas_ids = set()
        if remitos_asociados:
            for remito in remitos_asociados:
                for rp in getattr(remito, 'recepciones', []):
                    self._recepciones_asociadas_ids.add(rp.id_recepcion)
        self.txt_filtro.setEnabled(False)
        self.btn_buscar.setEnabled(False)
        self.btn_limpiar.setEnabled(False)
        self.cbo_dias.setEnabled(False)
        self.btn_volver_sin_cambios.setVisible(True)
        self.titulo_lbl.setText(
            f'<h2>Agregar Recepciones — Proveedor {id_proveedor} — Destino {nombre_destino}</h2>'
        )
        try:
            recepciones = self._svc_recepcion.buscar_por_proveedor_destino(
                id_proveedor, nombre_destino
            )
            self._recepciones_todas = recepciones
            self._recepciones_seleccionadas = []
            self._recepciones = recepciones
            self._cargar_tabla()
            self._actualizar_resumen()
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Error al buscar recepciones:\n{e}')

    def _limpiar(self):
        self._prefiltro_activo = False
        self._prefiltro_id_proveedor = ''
        self._prefiltro_nombre_destino = ''
        self._recepciones_asociadas_ids = set()
        self.txt_filtro.setEnabled(True)
        self.btn_buscar.setEnabled(True)
        self.btn_limpiar.setEnabled(True)
        self.cbo_dias.setEnabled(True)
        self.btn_volver_sin_cambios.setVisible(False)
        self.titulo_lbl.setText('<h2>Paso 1: Seleccionar Recepciones Previstas</h2>')
        self.txt_filtro.clear()
        self.cbo_dias.setCurrentIndex(len(self.OPCIONES_DIAS) - 1)
        for col in self.COL_FILTRO:
            self._filtros[col] = ''
            w = self.tabla_rp.cellWidget(0, col)
            if w:
                idx = w.findText('')
                if idx >= 0:
                    w.setCurrentIndex(idx)
        self._recepciones_todas = []
        self._recepciones = []
        self._recepciones_seleccionadas = []
        self._cargar_tabla()
        self._actualizar_resumen()

    def _buscar(self):
        if self._prefiltro_activo:
            return
        filtro = self.txt_filtro.text().strip()
        partes = filtro.split()
        if len(partes) > 1:
            self._buscar_por_ids(partes)
            return
        dias = self.OPCIONES_DIAS[self.cbo_dias.currentIndex()][1]
        destino = ''
        w_nom = self.tabla_rp.cellWidget(0, 7) if self.tabla_rp.rowCount() > 0 else None
        if w_nom and w_nom.currentText():
            destino = w_nom.currentText()
        try:
            self._recepciones_todas = self._svc_recepcion.buscar(filtro, dias, destino)
            self._recepciones_seleccionadas = []
            self._aplicar_filtros()
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Error al consultar recepciones previstas:\n{e}')
            self._recepciones_todas = []
            self._recepciones = []
            self._cargar_tabla()
            self._actualizar_resumen()
            self.btn_confirmar.setEnabled(False)

    def _buscar_por_ids(self, ids: list[str]):
        try:
            resultados = self._svc_recepcion.buscar_por_ids(ids)
            if not resultados:
                QMessageBox.information(
                    self, 'Sin Resultados',
                    'Ninguna de las recepciones ingresadas fue encontrada.'
                )
                return
            proveedores = {}
            for r in resultados:
                proveedores.setdefault(r.id_proveedor, []).append(r)
            if len(proveedores) > 1:
                detalle = '\n'.join(
                    f'{pid} ({rs.razon_social}): {", ".join(r.id_recepcion for r in rs)}'
                    for pid, rs in proveedores.items()
                )
                QMessageBox.warning(
                    self, 'Proveedores Diferentes',
                    f'Las recepciones pertenecen a distintos proveedores:\n\n{detalle}'
                )
                return
            self._recepciones_todas = resultados
            self._recepciones_seleccionadas = []
            self._aplicar_filtros()
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Error al consultar recepciones:\n{e}')

    def _aplicar_filtros(self):
        filtrados = self._recepciones_todas[:]
        for col, val in self._filtros.items():
            if val:
                if col == 2:
                    filtrados = [r for r in filtrados if r.descripcion_clase == val]
                elif col == 5:
                    filtrados = [r for r in filtrados if r.razon_social == val]
                elif col == 6:
                    filtrados = [r for r in filtrados if r.sucursal_destino == val]
                elif col == 7:
                    filtrados = [r for r in filtrados if r.nombre_destino == val]
        self._recepciones = filtrados
        self._recepciones_seleccionadas = []
        self._cargar_tabla()
        self._actualizar_resumen()

    def _on_filtro_changed(self, col, text):
        self._filtros[col] = text
        self._aplicar_filtros()

    def _cargar_tabla(self):
        self.tabla_rp.blockSignals(True)
        self.tabla_rp.setRowCount(len(self._recepciones) + 1)

        for col in range(len(self.COL_RP)):
            if col in self.COL_FILTRO:
                cbo = QComboBox()
                cbo.addItem('')
                if self._recepciones_todas:
                    valores = set()
                    for r in self._recepciones_todas:
                        if col == 2:
                            v = r.descripcion_clase
                        elif col == 5:
                            v = r.razon_social
                        elif col == 6:
                            v = r.sucursal_destino
                        elif col == 7:
                            v = r.nombre_destino
                        if v:
                            valores.add(v)
                    for v in sorted(valores):
                        cbo.addItem(v)
                idx = cbo.findText(self._filtros[col])
                if idx >= 0:
                    cbo.setCurrentIndex(idx)
                cbo.currentTextChanged.connect(
                    lambda text, c=col: self._on_filtro_changed(c, text)
                )
                self.tabla_rp.setCellWidget(0, col, cbo)
            else:
                item = QTableWidgetItem()
                item.setFlags(Qt.ItemIsEnabled)
                self.tabla_rp.setItem(0, col, item)
        self.tabla_rp.setRowHeight(0, 40)

        for i, r in enumerate(self._recepciones):
            row = i + 1
            ya_asociada = r.id_recepcion in self._recepciones_asociadas_ids
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            if ya_asociada:
                chk.setCheckState(Qt.Checked)
                chk.setFlags(Qt.ItemIsEnabled)
                chk.setToolTip('Recepción ya asociada a un remito existente')
            else:
                chk.setCheckState(Qt.Unchecked)
            self.tabla_rp.setItem(row, 0, chk)
            for col, val in [
                (1, r.id_recepcion),
                (2, r.descripcion_clase),
                (3, r.fecha_prevista.strftime('%d/%m/%Y') if r.fecha_prevista else ''),
                (4, r.id_proveedor),
                (5, r.razon_social),
                (6, r.sucursal_destino),
                (7, r.nombre_destino),
            ]:
                item = QTableWidgetItem(val)
                item.setTextAlignment(self.HEADER_ALIGN)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.tabla_rp.setItem(row, col, item)

            btn_ver = QPushButton()
            btn_ver.setIcon(QApplication.style().standardIcon(QStyle.SP_MessageBoxInformation))
            btn_ver.setToolTip('Ver materiales')
            btn_ver.setCursor(Qt.PointingHandCursor)
            btn_ver.clicked.connect(lambda _, idx=i: self._ver_materiales(idx))
            contenedor_btn = QWidget()
            lay_btn = QHBoxLayout(contenedor_btn)
            lay_btn.setContentsMargins(0, 0, 0, 0)
            lay_btn.addWidget(btn_ver)
            self.tabla_rp.setCellWidget(row, 8, contenedor_btn)
        self.tabla_rp.blockSignals(False)
        header = self.tabla_rp.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.tabla_rp.setColumnWidth(0, 30)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.tabla_rp.setColumnWidth(8, 35)
        for c in range(1, 8):
            header.setSectionResizeMode(c, QHeaderView.Stretch)

    def _on_cell_clicked(self, row, column):
        if column != 0:
            return
        if row <= 0 or row > len(self._recepciones):
            return
        rp = self._recepciones[row - 1]
        if rp.id_recepcion in self._recepciones_asociadas_ids:
            return
        item = self.tabla_rp.item(row, 0)
        if not item:
            return
        nuevo_estado = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
        item.setCheckState(nuevo_estado)
        self._on_checkbox_toggled(row, nuevo_estado)

    def _ver_materiales(self, idx: int):
        if idx < 0 or idx >= len(self._recepciones):
            return
        rp = self._recepciones[idx]
        try:
            materiales = self._svc_recepcion.buscar_materiales(rp.id_recepcion)
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Error al buscar materiales:\n{e}')
            return
        dlg = DialogoMateriales(rp.id_recepcion, materiales, self)
        dlg.exec_()

    def _on_checkbox_toggled(self, row, state):
        idx = row - 1
        if idx < 0 or idx >= len(self._recepciones):
            return
        rp = self._recepciones[idx]

        if state == Qt.Checked:
            temp = self._recepciones_seleccionadas + [rp]
            dests = {r.nombre_destino.strip().lower() for r in temp}
            if len(dests) > 1:
                item = self.tabla_rp.item(row, 0)
                if item:
                    item.setCheckState(Qt.Unchecked)
                distintos = list({(r.sucursal_destino, r.nombre_destino) for r in temp})
                detalle = '\n'.join(f'  {s} - {n}' for s, n in distintos)
                QMessageBox.warning(
                    self, 'Destinos Diferentes',
                    f'Las recepciones previstas seleccionadas tienen diferentes destinos:\n{detalle}\n\n'
                    'Todas deben pertenecer al mismo destino.'
                )
                return
            self._recepciones_seleccionadas = temp
        else:
            self._recepciones_seleccionadas = [
                r for r in self._recepciones_seleccionadas
                if r.id_recepcion != rp.id_recepcion
            ]
        self._actualizar_resumen()

    def eventFilter(self, obj, event):
        if obj is self.lbl_resumen and event.type() == QEvent.MouseButtonPress:
            if self._recepciones_seleccionadas:
                self._toggle_label()
            return True
        return super().eventFilter(obj, event)

    def _toggle_label(self):
        self._label_expanded = not self._label_expanded
        if self._label_expanded:
            self.lbl_resumen.setWordWrap(True)
            self.lbl_resumen.setText(self._resumen_full_text)
            self.lbl_resumen.setStyleSheet(
                'font-weight: bold; color: #2196F3; font-size: 13px; '
                'border: 1px solid #2196F3; padding: 4px;'
            )
        else:
            self.lbl_resumen.setWordWrap(False)
            fm = self.lbl_resumen.fontMetrics()
            self.lbl_resumen.setText(
                fm.elidedText(self._resumen_full_text, Qt.ElideRight, self.lbl_resumen.width())
            )
            self.lbl_resumen.setStyleSheet(
                'font-weight: bold; color: #2196F3; font-size: 13px;'
            )

    def _actualizar_resumen(self):
        self._label_expanded = False
        self.lbl_resumen.setWordWrap(False)
        self.lbl_resumen.setStyleSheet('font-weight: bold; color: #2196F3; font-size: 13px;')
        cant = len(self._recepciones_seleccionadas)
        if cant == 0:
            self._resumen_full_text = 'Ninguna recepción seleccionada.'
            self.btn_confirmar.setEnabled(False)
        else:
            destino = self._recepciones_seleccionadas[0].sucursal_destino
            nombre = self._recepciones_seleccionadas[0].nombre_destino
            ids = ', '.join(r.id_recepcion for r in self._recepciones_seleccionadas)
            self._resumen_full_text = (
                f'{cant} recepción(es): {ids} — Destino: {nombre} ({destino})'
            )
            self.btn_confirmar.setEnabled(True)
        fm = self.lbl_resumen.fontMetrics()
        self.lbl_resumen.setText(
            fm.elidedText(self._resumen_full_text, Qt.ElideRight, self.lbl_resumen.width())
        )
        self._calcular_resumen_seleccion()

    def _calcular_resumen_seleccion(self):
        if len(self._recepciones_seleccionadas) < 1:
            self.grp_resumen_seleccion.setVisible(False)
            return
        self.grp_resumen_seleccion.setVisible(True)
        cant = len(self._recepciones_seleccionadas)
        destinos = {r.nombre_destino.strip().lower() for r in self._recepciones_seleccionadas}
        total_previstas = 0
        total_recepcionadas = 0
        skus = set()
        for rp in self._recepciones_seleccionadas:
            try:
                materiales = self._svc_recepcion.buscar_materiales(rp.id_recepcion)
            except Exception:
                continue
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
                    skus.add(mat)
        self.lbl_resumen_recepciones.setText(f'Recepciones: {cant}')
        self.lbl_resumen_destinos.setText(f'Destinos: {len(destinos)}')
        self.lbl_resumen_skus.setText(f'SKU: {len(skus)}')
        self.lbl_resumen_previstas.setText(f'Previstas: {total_previstas:,.2f}')
        self.lbl_resumen_recepcionadas.setText(f'Recepcionadas: {total_recepcionadas:,.2f}')

    def _confirmar(self):
        if not self._recepciones_seleccionadas:
            QMessageBox.warning(
                self, 'Selección Incompleta',
                'Debe seleccionar al menos una recepción prevista.'
            )
            return

        dests = {r.nombre_destino.strip().lower() for r in self._recepciones_seleccionadas}
        if len(dests) > 1:
            QMessageBox.warning(
                self, 'Destinos Diferentes',
                'Las recepciones previstas seleccionadas tienen diferentes destinos.\n'
                'Todas deben pertenecer al mismo destino.'
            )
            return

        proveedor = self._recepciones_seleccionadas[0]
        if self._on_confirmar_callback:
            self._on_confirmar_callback(
                proveedor.id_proveedor,
                proveedor.razon_social,
                self._recepciones_seleccionadas
            )

    def showEvent(self, event):
        super().showEvent(event)
        if self.txt_filtro.isEnabled():
            self.txt_filtro.setFocus()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._label_expanded and self._resumen_full_text:
            fm = self.lbl_resumen.fontMetrics()
            self.lbl_resumen.setText(
                fm.elidedText(self._resumen_full_text, Qt.ElideRight, self.lbl_resumen.width())
            )

    @property
    def recepciones_seleccionadas(self) -> list[RecepcionPrevista]:
        return self._recepciones_seleccionadas
