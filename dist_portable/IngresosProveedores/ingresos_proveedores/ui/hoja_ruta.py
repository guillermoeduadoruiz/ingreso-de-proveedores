import os
from datetime import date

from PyQt5.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QDateEdit, QPushButton, QComboBox, QGroupBox, QTableWidget, QTableWidgetItem,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QInputDialog, QApplication, QSplitter,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QCursor, QFont, QBrush, QColor

from modelos.hoja_ruta import (
    HojaRuta, ESTADOS_HOJA, ESTADOS_REMITO, HR_EN_PREPARACION, HR_DESPACHADA,
    HR_ANULADA, agrupar_por_transporte,
)
from servicios.hoja_ruta_svc import HojaRutaService
from servicios.pdf_hoja_ruta import generar_pdf_hoja_ruta

COLS_ARBOL = ['Transporte / Destinatario / N° Remito', 'ID Ingreso', 'Fecha Ingreso', 'Emitido',
              'Proveedor', 'Bultos', 'Estado']
COL_BULTOS = 5
ROL_ID = Qt.UserRole
ROL_BULTOS = Qt.UserRole + 1


def _fmt_fecha(valor, con_hora: bool = False) -> str:
    if not valor:
        return ''
    return valor.strftime('%d/%m/%Y %H:%M' if con_hora else '%d/%m/%Y')


def _llenar_arbol(tree: QTreeWidget, remitos: list[dict], marcados: set[int] | None = None):
    """Carga remitos agrupados por transporte y, dentro, por destinatario.

    Con `marcados` los ítems son seleccionables (check en los tres niveles).
    """
    con_check = marcados is not None
    tree.blockSignals(True)
    tree.clear()
    negrita = QFont()
    negrita.setBold(True)
    fondo_transporte = QBrush(QColor('#E3F2FD'))
    for t in agrupar_por_transporte(remitos):
        nodo_t = QTreeWidgetItem([
            f"Transporte: {t['transporte']}",
            f"{len(t['destinatarios'])} destinatario(s)", f"{t['cantidad_remitos']} remito(s)",
            '', '', str(t['total_bultos']), '',
        ])
        for c in range(len(COLS_ARBOL)):
            nodo_t.setFont(c, negrita)
            nodo_t.setBackground(c, fondo_transporte)
        nodo_t.setTextAlignment(COL_BULTOS, Qt.AlignCenter)
        if con_check:
            nodo_t.setFlags(nodo_t.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
        tree.addTopLevelItem(nodo_t)
        for d in t['destinatarios']:
            domicilio = ', '.join(x for x in (d['domicilio'], d['ciudad']) if x)
            padre = QTreeWidgetItem([
                f"{d['nombre'] or d['sucursal']} ({d['sucursal']})",
                f"{len(d['remitos'])} remito(s)", '', '', domicilio, str(d['total_bultos']), '',
            ])
            for c in (0, COL_BULTOS):
                padre.setFont(c, negrita)
            padre.setTextAlignment(COL_BULTOS, Qt.AlignCenter)
            if con_check:
                padre.setFlags(padre.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            nodo_t.addChild(padre)
            for r in d['remitos']:
                prov = f"{r.get('num_proveedor') or ''} - {r.get('razon_social') or ''}".strip(' -')
                bultos = int(r.get('total_bultos') or 0)
                hijo = QTreeWidgetItem([
                    str(r.get('num_remito') or ''), str(r.get('id_ingreso') or ''),
                    _fmt_fecha(r.get('fecha_ingreso')), _fmt_fecha(r.get('fecha_generacion'), True),
                    prov, str(bultos), ESTADOS_REMITO.get(int(r.get('estado') or 1), ''),
                ])
                hijo.setTextAlignment(COL_BULTOS, Qt.AlignCenter)
                hijo.setData(0, ROL_ID, r['id_remito_generado'])
                hijo.setData(0, ROL_BULTOS, bultos)
                if con_check:
                    hijo.setFlags(hijo.flags() | Qt.ItemIsUserCheckable)
                    hijo.setCheckState(
                        0, Qt.Checked if r['id_remito_generado'] in marcados else Qt.Unchecked
                    )
                padre.addChild(hijo)
    tree.expandAll()
    header = tree.header()
    header.setSectionResizeMode(QHeaderView.ResizeToContents)
    header.setSectionResizeMode(4, QHeaderView.Stretch)
    tree.blockSignals(False)


def _nuevo_arbol() -> QTreeWidget:
    tree = QTreeWidget()
    tree.setColumnCount(len(COLS_ARBOL))
    tree.setHeaderLabels(COLS_ARBOL)
    tree.setAlternatingRowColors(True)
    tree.setSelectionMode(QAbstractItemView.NoSelection)
    tree.header().setStretchLastSection(False)
    return tree


class DialogoHojaRuta(QDialog):
    """Alta / edición de una hoja de ruta: datos del transporte + selección de remitos."""

    def __init__(self, svc: HojaRutaService, hoja: HojaRuta | None = None, parent=None):
        super().__init__(parent)
        self._svc = svc
        self._hoja = hoja or HojaRuta(fecha_despacho=date.today())
        self.resultado: HojaRuta | None = None
        self.imprimir = False
        self.setWindowTitle(
            'Nueva Hoja de Ruta' if not self._hoja.id_hoja
            else f'Hoja de Ruta N° {self._hoja.numero}'
        )
        self.setMinimumSize(1150, 720)
        self._setup_ui()
        self._cargar()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        grp_datos = QGroupBox('Datos del despacho')
        form = QFormLayout(grp_datos)
        fila1 = QHBoxLayout()
        self.dtp_fecha = QDateEdit()
        self.dtp_fecha.setCalendarPopup(True)
        self.dtp_fecha.setDisplayFormat('dd/MM/yyyy')
        f = self._hoja.fecha_despacho
        self.dtp_fecha.setDate(QDate(f.year, f.month, f.day))
        fila1.addWidget(self.dtp_fecha)
        fila1.addWidget(QLabel('Transportista:'))
        self.txt_transportista = QLineEdit(self._hoja.transportista)
        self.txt_transportista.setMaxLength(200)
        fila1.addWidget(self.txt_transportista, 2)
        fila1.addWidget(QLabel('Chofer:'))
        self.txt_chofer = QLineEdit(self._hoja.chofer)
        self.txt_chofer.setMaxLength(200)
        fila1.addWidget(self.txt_chofer, 2)
        fila1.addWidget(QLabel('Patente:'))
        self.txt_patente = QLineEdit(self._hoja.patente)
        self.txt_patente.setMaxLength(30)
        fila1.addWidget(self.txt_patente, 1)
        form.addRow('Fecha despacho:', fila1)
        self.txt_obs = QLineEdit(self._hoja.observaciones)
        self.txt_obs.setMaxLength(500)
        form.addRow('Observaciones:', self.txt_obs)
        layout.addWidget(grp_datos)

        grp_rem = QGroupBox('Remitos pendientes de despacho (agrupados por transporte y destinatario)')
        rem_layout = QVBoxLayout(grp_rem)
        barra = QHBoxLayout()
        self.txt_filtro = QLineEdit()
        self.txt_filtro.setPlaceholderText('Filtrar por transporte, destinatario, N° remito, ingreso o proveedor...')
        barra.addWidget(self.txt_filtro, 1)
        self.btn_marcar = QPushButton('Marcar visibles')
        self.btn_marcar.setObjectName('btnSecondary')
        barra.addWidget(self.btn_marcar)
        self.btn_desmarcar = QPushButton('Desmarcar todo')
        self.btn_desmarcar.setObjectName('btnSecondary')
        barra.addWidget(self.btn_desmarcar)
        rem_layout.addLayout(barra)
        self.arbol = _nuevo_arbol()
        rem_layout.addWidget(self.arbol, 1)
        self.lbl_resumen = QLabel('')
        self.lbl_resumen.setStyleSheet('font-size: 13px; color: #2196F3; font-weight: bold;')
        rem_layout.addWidget(self.lbl_resumen)
        layout.addWidget(grp_rem, 1)

        botones = QHBoxLayout()
        self.btn_cancelar = QPushButton('Cancelar')
        self.btn_cancelar.setObjectName('btnSecondary')
        botones.addWidget(self.btn_cancelar)
        botones.addStretch(1)
        self.btn_guardar = QPushButton('Guardar')
        self.btn_guardar.setObjectName('btnPrimary')
        botones.addWidget(self.btn_guardar)
        self.btn_guardar_imprimir = QPushButton('Guardar e Imprimir')
        self.btn_guardar_imprimir.setObjectName('btnSuccess')
        botones.addWidget(self.btn_guardar_imprimir)
        layout.addLayout(botones)

        self.arbol.itemChanged.connect(lambda *_: self._actualizar_resumen())
        self.txt_filtro.textChanged.connect(self._filtrar)
        self.btn_marcar.clicked.connect(lambda: self._marcar(True))
        self.btn_desmarcar.clicked.connect(lambda: self._marcar(False))
        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_guardar.clicked.connect(lambda: self._guardar(False))
        self.btn_guardar_imprimir.clicked.connect(lambda: self._guardar(True))

    def _cargar(self):
        try:
            pendientes = self._svc.obtener_pendientes(self._hoja.id_hoja)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error al cargar remitos pendientes:\n{e}')
            pendientes = []
        marcados = {r['id_remito_generado'] for r in self._hoja.remitos}
        _llenar_arbol(self.arbol, pendientes, marcados)
        if not pendientes:
            self.lbl_resumen.setText('No hay remitos pendientes de despacho.')
        else:
            self._actualizar_resumen()

    def _hijos(self):
        """Recorre (transporte, destinatario, remito)."""
        for i in range(self.arbol.topLevelItemCount()):
            nodo_t = self.arbol.topLevelItem(i)
            for j in range(nodo_t.childCount()):
                padre = nodo_t.child(j)
                for k in range(padre.childCount()):
                    yield nodo_t, padre, padre.child(k)

    def _seleccionados(self) -> list[QTreeWidgetItem]:
        return [h for _, _, h in self._hijos() if h.checkState(0) == Qt.Checked]

    def _actualizar_resumen(self):
        sel = self._seleccionados()
        destinos = {id(h.parent()) for h in sel}
        transportes = {id(h.parent().parent()) for h in sel}
        bultos = sum(int(h.data(0, ROL_BULTOS) or 0) for h in sel)
        self.lbl_resumen.setText(
            f'Seleccionados: {len(transportes)} transporte(s)  |  {len(destinos)} destinatario(s)  |  '
            f'{len(sel)} remito(s)  |  {bultos} bulto(s)'
        )

    def _filtrar(self, texto: str):
        texto = texto.strip().lower()
        for i in range(self.arbol.topLevelItemCount()):
            nodo_t = self.arbol.topLevelItem(i)
            t_ok = not texto or texto in nodo_t.text(0).lower()
            alguno_t = False
            for j in range(nodo_t.childCount()):
                padre = nodo_t.child(j)
                padre_ok = t_ok or texto in padre.text(0).lower() or texto in padre.text(4).lower()
                alguno = False
                for k in range(padre.childCount()):
                    hijo = padre.child(k)
                    ok = padre_ok or any(texto in hijo.text(c).lower() for c in range(len(COLS_ARBOL)))
                    hijo.setHidden(not ok)
                    alguno = alguno or ok
                padre.setHidden(not alguno)
                alguno_t = alguno_t or alguno
            nodo_t.setHidden(not alguno_t)

    def _marcar(self, marcar: bool):
        self.arbol.blockSignals(True)
        for nodo_t, padre, hijo in self._hijos():
            if marcar and (nodo_t.isHidden() or padre.isHidden() or hijo.isHidden()):
                continue
            hijo.setCheckState(0, Qt.Checked if marcar else Qt.Unchecked)
        self.arbol.blockSignals(False)
        self.arbol.viewport().update()
        self._actualizar_resumen()

    def _guardar(self, imprimir: bool):
        ids = [int(h.data(0, ROL_ID)) for h in self._seleccionados()]
        if not ids:
            QMessageBox.warning(self, 'Hoja de Ruta', 'Seleccione al menos un remito.')
            return
        h = self._hoja
        h.fecha_despacho = self.dtp_fecha.date().toPyDate()
        h.transportista = self.txt_transportista.text()
        h.chofer = self.txt_chofer.text()
        h.patente = self.txt_patente.text()
        h.observaciones = self.txt_obs.text()
        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            self.resultado = self._svc.guardar(h, ids)
        except ValueError as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, 'Hoja de Ruta', str(e))
            return
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, 'Error', f'Error al guardar la hoja de ruta:\n{e}')
            return
        QApplication.restoreOverrideCursor()
        self.imprimir = imprimir
        self.accept()


class HojaRutaWidget(QWidget):
    COL_NAMES = ['N° Hoja', 'Fecha Despacho', 'Transportista', 'Chofer', 'Patente',
                 'Destinatarios', 'Remitos', 'Bultos', 'Estado']

    def __init__(self, svc: HojaRutaService, clave_anulacion: str = ''):
        super().__init__()
        self._svc = svc
        self._clave_anulacion = clave_anulacion
        self._hojas: list[HojaRuta] = []
        self._id_seleccionado: int | None = None
        self._on_volver_callback = None
        self._setup_ui()

    # ---- UI ----
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(QLabel('<h2>Hojas de Ruta</h2>'))

        self.lbl_pendientes = QLabel('')
        self.lbl_pendientes.setStyleSheet('font-size: 13px; color: #E65100; font-weight: bold;')
        layout.addWidget(self.lbl_pendientes)

        filtro = QHBoxLayout()
        filtro.addWidget(QLabel('Despacho desde:'))
        self.dtp_desde = QDateEdit()
        self.dtp_desde.setCalendarPopup(True)
        self.dtp_desde.setDisplayFormat('dd/MM/yyyy')
        self.dtp_desde.setDate(QDate.currentDate().addMonths(-1))
        filtro.addWidget(self.dtp_desde)
        filtro.addWidget(QLabel('Hasta:'))
        self.dtp_hasta = QDateEdit()
        self.dtp_hasta.setCalendarPopup(True)
        self.dtp_hasta.setDisplayFormat('dd/MM/yyyy')
        self.dtp_hasta.setDate(QDate.currentDate().addMonths(1))
        filtro.addWidget(self.dtp_hasta)
        filtro.addWidget(QLabel('Estado:'))
        self.cmb_estado = QComboBox()
        self.cmb_estado.addItem('Todos', None)
        for cod, desc in ESTADOS_HOJA.items():
            self.cmb_estado.addItem(desc, cod)
        filtro.addWidget(self.cmb_estado)
        filtro.addStretch(1)
        self.btn_buscar = QPushButton('Buscar')
        self.btn_buscar.setObjectName('btnPrimary')
        filtro.addWidget(self.btn_buscar)
        layout.addLayout(filtro)

        splitter = QSplitter(Qt.Vertical)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(self.COL_NAMES))
        self.tabla.setHorizontalHeaderLabels(self.COL_NAMES)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        splitter.addWidget(self.tabla)

        grp_det = QGroupBox('Detalle por transporte y destinatario')
        det_layout = QVBoxLayout(grp_det)
        self.lbl_detalle = QLabel('')
        self.lbl_detalle.setStyleSheet('font-size: 12px; color: #2196F3; font-weight: bold;')
        det_layout.addWidget(self.lbl_detalle)
        self.arbol = _nuevo_arbol()
        det_layout.addWidget(self.arbol, 1)
        splitter.addWidget(grp_det)
        splitter.setSizes([300, 400])
        layout.addWidget(splitter, 1)

        acciones = QHBoxLayout()
        self.btn_volver = QPushButton('← Volver')
        self.btn_volver.setObjectName('btnSecondary')
        acciones.addWidget(self.btn_volver)
        acciones.addStretch(1)
        self.btn_nueva = QPushButton('Nueva Hoja de Ruta')
        self.btn_nueva.setObjectName('btnSuccess')
        acciones.addWidget(self.btn_nueva)
        self.btn_editar = QPushButton('Editar')
        self.btn_editar.setObjectName('btnPrimary')
        acciones.addWidget(self.btn_editar)
        self.btn_imprimir = QPushButton('Imprimir')
        self.btn_imprimir.setObjectName('btnPrimary')
        acciones.addWidget(self.btn_imprimir)
        self.btn_confirmar = QPushButton('Confirmar Despacho')
        self.btn_confirmar.setObjectName('btnSuccess')
        acciones.addWidget(self.btn_confirmar)
        self.btn_anular = QPushButton('Anular')
        self.btn_anular.setObjectName('btnDanger')
        acciones.addWidget(self.btn_anular)
        layout.addLayout(acciones)

        self.btn_buscar.clicked.connect(self._cargar_datos)
        self.cmb_estado.currentIndexChanged.connect(self._cargar_datos)
        self.tabla.itemSelectionChanged.connect(self._on_seleccion)
        self.tabla.itemDoubleClicked.connect(lambda *_: self._editar())
        self.btn_volver.clicked.connect(self._volver)
        self.btn_nueva.clicked.connect(self._nueva)
        self.btn_editar.clicked.connect(self._editar)
        self.btn_imprimir.clicked.connect(lambda: self._imprimir(self._hoja_actual()))
        self.btn_confirmar.clicked.connect(self._confirmar)
        self.btn_anular.clicked.connect(self._anular)
        self._actualizar_botones()

    def set_on_volver(self, callback):
        self._on_volver_callback = callback

    def _volver(self):
        if self._on_volver_callback:
            self._on_volver_callback()

    # ---- Datos ----
    def cargar_datos(self):
        self._cargar_datos()

    def _cargar_datos(self):
        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            pendientes = self._svc.obtener_pendientes()
            self._hojas = self._svc.listar(
                self.dtp_desde.date().toPyDate(), self.dtp_hasta.date().toPyDate(),
                self.cmb_estado.currentData(),
            )
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, 'Error', f'Error al cargar hojas de ruta:\n{e}')
            return
        QApplication.restoreOverrideCursor()

        n_dest = len({r.get('sucursal_destino') for r in pendientes})
        bultos = sum(int(r.get('total_bultos') or 0) for r in pendientes)
        self.lbl_pendientes.setText(
            f'Pendientes de despacho (sin hoja de ruta): {len(pendientes)} remito(s) '
            f'para {n_dest} destinatario(s) — {bultos} bulto(s)'
            if pendientes else 'No hay remitos pendientes de despacho.'
        )
        self._poblar_tabla()

    def _poblar_tabla(self):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(len(self._hojas))
        fila_sel = -1
        for i, h in enumerate(self._hojas):
            valores = [h.numero, _fmt_fecha(h.fecha_despacho), h.transportista, h.chofer,
                       h.patente, str(len(h.destinatarios)), str(len(h.remitos)),
                       str(h.total_bultos), h.descripcion_estado]
            for c, v in enumerate(valores):
                item = QTableWidgetItem(v)
                if c in (0, 1, 5, 6, 7, 8):
                    item.setTextAlignment(Qt.AlignCenter)
                if h.estado == HR_ANULADA:
                    item.setForeground(Qt.gray)
                self.tabla.setItem(i, c, item)
            if h.id_hoja == self._id_seleccionado:
                fila_sel = i
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla.blockSignals(False)
        if self._hojas:
            self.tabla.selectRow(fila_sel if fila_sel >= 0 else 0)
        self._on_seleccion()

    def _hoja_actual(self) -> HojaRuta | None:
        filas = self.tabla.selectionModel().selectedRows() if self.tabla.selectionModel() else []
        if not filas:
            return None
        row = filas[0].row()
        return self._hojas[row] if 0 <= row < len(self._hojas) else None

    def _on_seleccion(self):
        h = self._hoja_actual()
        self._id_seleccionado = h.id_hoja if h else None
        if h:
            _llenar_arbol(self.arbol, h.remitos)
            txt = (f'Hoja N° {h.numero} — {h.descripcion_estado}  |  {len(h.destinatarios)} destinatario(s)'
                   f'  |  {len(h.remitos)} remito(s)  |  {h.total_bultos} bulto(s)')
            if h.despachado:
                txt += f'  |  Despachada el {_fmt_fecha(h.despachado, True)}'
            self.lbl_detalle.setText(txt)
        else:
            self.arbol.clear()
            self.lbl_detalle.setText('')
        self._actualizar_botones()

    def _actualizar_botones(self):
        h = self._hoja_actual()
        en_prep = bool(h) and h.estado == HR_EN_PREPARACION
        self.btn_editar.setEnabled(en_prep)
        self.btn_confirmar.setEnabled(en_prep)
        self.btn_imprimir.setEnabled(bool(h))
        self.btn_anular.setEnabled(bool(h) and h.estado != HR_ANULADA)

    # ---- Acciones ----
    def _abrir_dialogo(self, hoja: HojaRuta | None):
        dlg = DialogoHojaRuta(self._svc, hoja, self)
        if dlg.exec_() != QDialog.Accepted or not dlg.resultado:
            return
        self._id_seleccionado = dlg.resultado.id_hoja
        self._cargar_datos()
        if dlg.imprimir:
            self._imprimir(dlg.resultado)

    def _nueva(self):
        self._abrir_dialogo(None)

    def _editar(self):
        h = self._hoja_actual()
        if not h or h.estado != HR_EN_PREPARACION:
            return
        # Recargar desde la base por si otro puesto la modificó.
        try:
            h = self._svc.obtener(h.id_hoja)
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error al leer la hoja de ruta:\n{e}')
            return
        if not h or h.estado != HR_EN_PREPARACION:
            QMessageBox.warning(self, 'Hoja de Ruta', 'La hoja de ruta ya no está en preparación.')
            self._cargar_datos()
            return
        self._abrir_dialogo(h)

    def _imprimir(self, hoja: HojaRuta | None):
        if not hoja:
            return
        try:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            path = generar_pdf_hoja_ruta(hoja)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, 'Error', f'Error al generar la hoja de ruta:\n{e}')
            return
        QApplication.restoreOverrideCursor()
        try:
            os.startfile(path)
        except Exception as e:
            QMessageBox.information(self, 'Hoja de Ruta', f'PDF generado en:\n{path}\n\n({e})')

    def _confirmar(self):
        h = self._hoja_actual()
        if not h or h.estado != HR_EN_PREPARACION:
            return
        resp = QMessageBox.question(
            self, 'Confirmar Despacho',
            f'¿Confirmar el despacho de la hoja de ruta N° {h.numero}?\n\n'
            f'{len(h.destinatarios)} destinatario(s), {len(h.remitos)} remito(s), '
            f'{h.total_bultos} bulto(s).\n\n'
            'Los remitos pasarán a estado "Despachado" y la hoja ya no podrá editarse.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        try:
            self._svc.confirmar_despacho(h.id_hoja)
        except ValueError as e:
            QMessageBox.warning(self, 'Hoja de Ruta', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error al confirmar el despacho:\n{e}')
        self._cargar_datos()

    def _anular(self):
        h = self._hoja_actual()
        if not h or h.estado == HR_ANULADA:
            return
        aviso = ('Los remitos volverán al estado que tenían antes del despacho y quedarán '
                 'nuevamente pendientes.' if h.estado == HR_DESPACHADA
                 else 'Los remitos quedarán nuevamente pendientes de despacho.')
        resp = QMessageBox.question(
            self, 'Anular Hoja de Ruta',
            f'¿Anular la hoja de ruta N° {h.numero} ({h.descripcion_estado})?\n\n{aviso}',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return
        if h.estado == HR_DESPACHADA and self._clave_anulacion:
            clave, ok = QInputDialog.getText(
                self, 'Validación de Seguridad',
                'La hoja ya fue despachada. Ingrese la palabra clave para anularla:',
                QLineEdit.Password,
            )
            if not ok:
                return
            if clave != self._clave_anulacion:
                QMessageBox.warning(self, 'Acceso Denegado', 'La palabra clave es incorrecta.')
                return
        try:
            self._svc.anular(h.id_hoja)
        except ValueError as e:
            QMessageBox.warning(self, 'Hoja de Ruta', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Error al anular la hoja de ruta:\n{e}')
        self._cargar_datos()
