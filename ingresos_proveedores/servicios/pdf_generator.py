import os
import re
import time
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib.units import mm as mm_unit
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.barcode import code128 as _bc_code128
from reportlab.graphics.shapes import Drawing
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from modelos.ingreso import Ingreso
from database.conexiones import ConfigImpresion, ConfigImpresoras
from utils.paths import pdfs_dir as _pdfs_dir, assets_dir as _assets_dir

# Cada bulto imprime una única etiqueta física (sin duplicado apilado). El
# layout de la etiqueta vive en dp_generator (bloque LAYOUT), común a DP y PDF.


def _DIR_PDFS():
    return _pdfs_dir()


def _mm(val: float) -> float:
    return val * mm_unit


def _dir_remitos() -> str:
    p = os.path.join(_DIR_PDFS(), 'remitos')
    os.makedirs(p, exist_ok=True)
    return p


def _colectar_rps(destino: dict) -> str:
    vistos: set[str] = set()
    partes: list[str] = []
    for remito in destino.get('remitos', []):
        for rp in remito.recepciones:
            if rp.id_recepcion not in vistos:
                vistos.add(rp.id_recepcion)
                partes.append(rp.id_recepcion)
    return ', '.join(partes)


def _dir_etiquetas() -> str:
    p = os.path.join(_DIR_PDFS(), 'etiquetas')
    os.makedirs(p, exist_ok=True)
    return p


def _fmt_num_remito(num: str) -> str:
    """Normalize supplier remito number to 99999-99999999 format."""
    digits = re.sub(r'\D', '', num or '')
    if not digits:
        return num or ''
    right = digits[-8:]
    head = digits[:-8]
    if len(head) > 5:
        head = head[-5:]
    head = head.zfill(5)
    return f'{head}-{right}'


def generar_remito(
    ingreso: Ingreso,
    destino: dict,
    remitente: ConfigImpresion,
    cfg: ConfigImpresoras,
    num_remito: str,
) -> str:
    filename = f'{ingreso.id_ingreso}_{destino.get("sucursal", "") or destino.get("destino", "")}.pdf'
    filepath = os.path.join(_dir_remitos(), filename)
    tmp_path = os.path.join(
        _dir_remitos(), f'.tmp_{ingreso.id_ingreso}_{int(time.time() * 1000)}.pdf'
    )

    page_w, page_h = A4  # points

    def _y_top(y_top_mm: float) -> float:
        """Convert mm-from-top to reportlab y (from bottom of page)."""
        return page_h - y_top_mm * mm_unit

    def _fmtv(v: float) -> str:
        """Format currency $XX.XXX,XX (argentine style)."""
        if v <= 0:
            return '-'
        int_part = int(v)
        dec_part = round((v - int_part) * 100)
        s_int = f'{int_part:,}'.replace(',', '.')
        return f'${s_int},{dec_part:02d}'

    def _draw_num_right(text: str, x_right_mm: float, y: float,
                        size: float, max_w_mm: float):
        """Right-align text auto-reducing the font so it fits in max_w_mm."""
        font = 'Helvetica'
        w = stringWidth(text, font, size) / mm_unit
        while w > max_w_mm and size > 5:
            size -= 0.5
            w = stringWidth(text, font, size) / mm_unit
        c.setFont(font, size)
        c.drawRightString(_mm(x_right_mm), y, text)

    c = canvas.Canvas(tmp_path, pagesize=A4)

    # ── POSITIONS (mm from top-left, derived from 300 dpi preimpreso scan) ──
    # FECHA
    FECHA_X = 142.0
    FECHA_Y_TOP = 19.5
    # CLIENTE block
    CLIENTE_X = 29.6
    CLIENTE_NOMBRE_Y = 45.0
    CLIENTE_DOMICILIO_Y = 48.3
    CLIENTE_CP_CIUDAD_Y = 51.1
    # PROVEEDOR (razón social) above the items table
    PROVEEDOR_X = 29.6
    PROVEEDOR_Y_TOP = 73.0
    # ITEM table columns (x positions; right-aligned where noted)
    TBL_X_COD = 25.4      # N° remito (left-aligned)
    TBL_X_TIT = 51.2      # Fecha remito (left-aligned)
    TBL_X_EJ_END = 124.9  # Bultos (right-aligned)
    TBL_X_DESP_END = 145.6  # Unidades (right-aligned)
    TBL_X_PREC_END = 165.9  # Valor unitario (right-aligned)
    TBL_X_IMP_END = 193.9  # Valor total (right-aligned)
    TBL_ROW_Y_TOP = 95.0
    TBL_ROW_PITCH = 8.0
    # FLETE line
    FLETE_X = 53.0
    FLETE_Y_TOP = 164.4
    # QR de trazabilidad (esquina inferior izquierda)
    QR_X = 15.0
    QR_Y_TOP = 213.0
    QR_SIZE_MM = 25.0

    fs_normal = 9
    fs_small = 8

    # ── 2. FECHA ──
    c.setFont('Helvetica', fs_normal)
    c.drawString(_mm(FECHA_X), _y_top(FECHA_Y_TOP),
                 ingreso.fecha_ingreso.strftime('%d/%m/%Y'))

    # ── 3. CLIENTE ──
    rp_cliente = None
    for rem in destino.get('remitos', []):
        if rem.recepciones:
            rp_cliente = rem.recepciones[0]
            break

    nombre = rp_cliente.nombre_destino if rp_cliente else destino.get('destino', '')
    c.setFont('Helvetica-Bold', fs_normal)
    c.drawString(_mm(CLIENTE_X), _y_top(CLIENTE_NOMBRE_Y), nombre)

    domicilio = rp_cliente.domicilio_cliente if rp_cliente else ''
    c.setFont('Helvetica', fs_normal)
    c.drawString(_mm(CLIENTE_X), _y_top(CLIENTE_DOMICILIO_Y), domicilio)

    cp_parts: list[str] = []
    if rp_cliente:
        if rp_cliente.codigo_postal_cliente:
            cp_parts.append(rp_cliente.codigo_postal_cliente)
        if rp_cliente.ciudad_cliente:
            cp_parts.append(rp_cliente.ciudad_cliente)
        if rp_cliente.distrito_cliente:
            cp_parts.append(rp_cliente.distrito_cliente)
    c.setFont('Helvetica', fs_normal)
    c.drawString(_mm(CLIENTE_X), _y_top(CLIENTE_CP_CIUDAD_Y), ' '.join(cp_parts))

    # ── 3b. PROVEEDOR (razón social) ──
    c.setFont('Helvetica-Bold', fs_normal)
    c.drawString(_mm(PROVEEDOR_X), _y_top(PROVEEDOR_Y_TOP),
                 ingreso.proveedor.descripcion)

    # ── 4. ITEM ROWS (remitos del ingreso) ──
    remitos_grupo = destino.get('remitos', [])
    total_unidades = sum(rem.cantidad_unidades for rem in remitos_grupo)
    tiene_unidades = total_unidades > 0

    # Encabezados del cuerpo del remito
    y_header = TBL_ROW_Y_TOP - TBL_ROW_PITCH
    c.setFont('Helvetica-Bold', fs_small)
    c.drawString(_mm(TBL_X_COD), _y_top(y_header), 'Remito proveedor')
    c.drawString(_mm(TBL_X_TIT), _y_top(y_header), 'Fecha')
    c.drawRightString(_mm(TBL_X_EJ_END), _y_top(y_header), 'Bultos')
    if tiene_unidades:
        c.drawRightString(_mm(TBL_X_DESP_END), _y_top(y_header), 'Unidades')
        c.drawRightString(_mm(TBL_X_PREC_END), _y_top(y_header), 'Valor Unit.')
        c.drawRightString(_mm(TBL_X_IMP_END), _y_top(y_header), 'Valor Total')

    y_top = TBL_ROW_Y_TOP
    for rem in remitos_grupo:
        c.setFont('Helvetica-Bold', 7)
        c.drawString(_mm(TBL_X_COD), _y_top(y_top), _fmt_num_remito(rem.num_remito))

        c.setFont('Helvetica', fs_small)
        c.drawString(_mm(TBL_X_TIT), _y_top(y_top),
                     rem.fecha_remito.strftime('%d/%m/%Y'))
        c.drawRightString(_mm(TBL_X_EJ_END), _y_top(y_top),
                          str(rem.cantidad_bultos))
        if rem.cantidad_unidades > 0:
            _draw_num_right(str(rem.cantidad_unidades),
                            TBL_X_DESP_END, _y_top(y_top), fs_small,
                            TBL_X_PREC_END - TBL_X_DESP_END)
            _draw_num_right(_fmtv(rem.valor_declarado_unitario),
                            TBL_X_PREC_END, _y_top(y_top), fs_small,
                            TBL_X_PREC_END - TBL_X_DESP_END)
            _draw_num_right(_fmtv(rem.valor_declarado_total),
                            TBL_X_IMP_END, _y_top(y_top), fs_small,
                            TBL_X_IMP_END - TBL_X_PREC_END)
        y_top += TBL_ROW_PITCH

    # ── 5. FLETE PAGO EN DESTINO (value, label is pre-printed) ──
    flete_text = 'FLETE PAGO EN DESTINO'
    if rp_cliente and rp_cliente.transporte_descripcion:
        flete_text = rp_cliente.transporte_descripcion
    c.setFont('Helvetica-Bold', fs_normal)
    c.drawString(_mm(FLETE_X), _y_top(FLETE_Y_TOP), flete_text)

    # ── 6. TOTALES (en la zona central libre, tras la última fila) ──
    total_bultos = destino.get('total_bultos', 0)
    total_vd = sum(rem.valor_declarado_total for rem in remitos_grupo)
    c.setFont('Helvetica-Bold', fs_normal)
    y_tot = TBL_ROW_Y_TOP + (len(remitos_grupo) + 1) * TBL_ROW_PITCH
    if tiene_unidades:
        linea_total = f'Total de Unidades: {total_unidades}   Total Bultos: {total_bultos}'
    else:
        linea_total = f'Total Bultos: {total_bultos}'
    c.drawString(_mm(TBL_X_COD), _y_top(y_tot), linea_total)
    if total_vd > 0:
        c.drawString(_mm(TBL_X_COD), _y_top(y_tot + TBL_ROW_PITCH),
                     f'{_fmtv(total_vd)} <<== Total valorizado')

    # ── 7. QR DE TRAZABILIDAD ──
    qr_lines = [
        f'ING: {ingreso.id_ingreso}',
        f'SUC: {destino.get("sucursal", "") or destino.get("destino", "")}',
        f'FECHA: {ingreso.fecha_ingreso.strftime("%d/%m/%Y")}',
        f'PROV: {ingreso.proveedor.descripcion}',
        f'DEST: {nombre}',
        f'BULTOS: {total_bultos}',
    ]
    if total_unidades > 0:
        qr_lines.append(f'UNIDADES: {total_unidades}')
    if total_vd > 0:
        qr_lines.append(f'VALOR DECLARADO: {_fmtv(total_vd)}')
    if num_remito:
        qr_lines.append(f'REM: {num_remito}')
    qr_text = '\n'.join(qr_lines)
    qr = QrCodeWidget(qr_text)
    qr.barWidth = _mm(QR_SIZE_MM)
    qr.barHeight = _mm(QR_SIZE_MM)
    d = Drawing(_mm(QR_SIZE_MM), _mm(QR_SIZE_MM))
    d.add(qr)
    d.drawOn(c, _mm(QR_X), _y_top(QR_Y_TOP + QR_SIZE_MM))

    # ── 7b. Contenido del QR legible a la derecha ──
    QR_TEXT_X = QR_X + QR_SIZE_MM + 4.0
    y_line = QR_Y_TOP + 4.0
    c.setFont('Helvetica', fs_normal)
    for line in qr_lines:
        c.drawString(_mm(QR_TEXT_X), _y_top(y_line), line)
        y_line += 5.0

    c.save()

    try:
        os.replace(tmp_path, filepath)
    except OSError:
        # El archivo destino está en uso (p. ej. abierto en el visor):
        # se entrega un archivo con nombre único para no pisar el abierto.
        filepath = os.path.join(
            _dir_remitos(),
            f'{ingreso.id_ingreso}_{destino.get("sucursal", "") or destino.get("destino", "")}'
            f'.{datetime.now().strftime("%Y%m%d-%H%M%S")}.pdf'
        )
        try:
            os.replace(tmp_path, filepath)
        except OSError:
            filepath = tmp_path
    return filepath


def generar_etiquetas(
    ingreso: Ingreso,
    destino: dict,
    cfg: ConfigImpresoras,
    remitente: ConfigImpresion,
    num_remito: str = '',
) -> str:
    # (2026-09-23) El PDF replica la etiqueta DP: mismas dimensiones (una
    # etiqueta de ETQ_ANCHO_MM x ETQ_ALTO_MM por página, sin márgenes de hoja
    # ni grilla) y la MISMA estructura, porque dibuja los elementos que arma
    # `dp_generator.layout_etiqueta` a partir de las constantes de LAYOUT.
    # Import local: dp_generator importa este módulo (global sería circular).
    from servicios.dp_generator import (
        DPI, ETQ_ANCHO_MM, ETQ_ALTO_MM, QR_LADO_MM,
        layout_etiqueta, parametros_etiqueta,
    )
    _, _, marg_t_mm, marg_r_mm = parametros_etiqueta(cfg)
    page_w = _mm(ETQ_ANCHO_MM)
    page_h = _mm(ETQ_ALTO_MM)
    total = destino['total_bultos']

    rps = _colectar_rps(destino)
    rps_codigos = [r.strip() for r in rps.split(',') if r.strip()]
    fecha_str = ingreso.fecha_ingreso.strftime('%d/%m/%Y')

    rp_cliente = None
    for rem in destino.get('remitos', []):
        if rem.recepciones:
            rp_cliente = rem.recepciones[0]
            break

    muelle_despacho = rp_cliente.transporte_datos_privados if rp_cliente else ''

    remitos_prov: list[str] = []
    _vistos_rem_prov: set[str] = set()
    for rem in destino.get('remitos', []):
        if rem.num_remito and rem.num_remito not in _vistos_rem_prov:
            _vistos_rem_prov.add(rem.num_remito)
            remitos_prov.append(_fmt_num_remito(rem.num_remito))
    remitos_prov_str = ', '.join(remitos_prov)

    qr_data = ''
    if muelle_despacho:
        qr_data = (
            f'Proveedor: {ingreso.proveedor.descripcion}\n'
            f'Destino: {destino["destino"]}\n'
            f'Sucursal: {destino["sucursal"]}\n'
        )
        if remitos_prov_str:
            qr_data += f'Remito Prov: {remitos_prov_str}\n'
        if rp_cliente:
            if rp_cliente.domicilio_cliente:
                qr_data += f'Domicilio: {rp_cliente.domicilio_cliente}\n'
            if rp_cliente.codigo_postal_cliente:
                qr_data += f'CP: {rp_cliente.codigo_postal_cliente}\n'
            if rp_cliente.ciudad_cliente:
                qr_data += f'Ciudad: {rp_cliente.ciudad_cliente}\n'
            if rp_cliente.distrito_cliente:
                qr_data += f'Distrito: {rp_cliente.distrito_cliente}\n'
            if rp_cliente.transporte_descripcion:
                qr_data += f'Transporte: {rp_cliente.transporte_descripcion}\n'
        qr_data += f'Muelle de despacho: {muelle_despacho}\n'
        qr_data += f'Fecha: {fecha_str}\n'
        qr_data += f'RP: {rps}\n'
        qr_data += f'Remitente: {remitente.remitente_nombre}'

    filename = f'{ingreso.id_ingreso}_{destino["sucursal"]}_etiquetas.pdf'
    filepath = os.path.join(_dir_etiquetas(), filename)
    tmp_path = os.path.join(
        _dir_etiquetas(), f'.tmp_{ingreso.id_ingreso}_{int(time.time() * 1000)}_etiquetas.pdf'
    )

    c = canvas.Canvas(tmp_path, pagesize=(page_w, page_h))

    def _mm_de_dots(d: int) -> float:
        return d * 25.4 / DPI

    for idx in range(total):
        elems = layout_etiqueta(
            ETQ_ANCHO_MM, ETQ_ALTO_MM, marg_t_mm, marg_r_mm,
            ingreso.proveedor.descripcion,
            destino.get('destino', ''),
            destino.get('sucursal', ''),
            rp_cliente, fecha_str, remitente,
            rps_codigos, qr_data, muelle_despacho,
            idx + 1, total,
            remitos_prov_str, num_remito,
        )
        for e in elems:
            if e[0] == 'qr':
                # Esquina superior izquierda en (x, y), lado QR_LADO_MM.
                _, x, y, data = e
                lado = _mm(QR_LADO_MM)
                qr = QrCodeWidget(data)
                qr.barWidth = lado
                qr.barHeight = lado
                d = Drawing(lado, lado)
                d.add(qr)
                d.drawOn(c, _mm(_mm_de_dots(x)), page_h - _mm(_mm_de_dots(y)) - lado)
                continue
            # Texto: `y` es el borde superior de la línea; la línea base queda
            # una altura de mayúscula (0.718 em en Helvetica) más abajo.
            # Helvetica = métricas de Swiss 721, la fuente de la PC42t.
            _, x, y, texto, pt, bold, _max_por_pt = e
            c.setFont('Helvetica-Bold' if bold else 'Helvetica', pt)
            c.drawString(
                _mm(_mm_de_dots(x)),
                page_h - _mm(_mm_de_dots(y)) - pt * 0.718,
                texto,
            )
        c.showPage()

    c.save()

    try:
        os.replace(tmp_path, filepath)
    except OSError:
        # Archivo destino en uso: nombre único para no pisar el PDF abierto.
        filepath = os.path.join(
            _dir_etiquetas(),
            f'{ingreso.id_ingreso}_{destino["sucursal"]}_etiquetas'
            f'.{datetime.now().strftime("%Y%m%d-%H%M%S")}.pdf'
        )
        try:
            os.replace(tmp_path, filepath)
        except OSError:
            filepath = tmp_path
    return filepath


def _dibujar_etiqueta_mateti(c, mat, x0, ph, mt, etq_w, etq_h):
    usable_w = etq_w
    cx = x0 + usable_w / 2
    ean = (mat.get('barcode', '') or '').strip()
    codigo = mat.get('codigo', '')
    descripcion = mat.get('descripcion', '')
    um = mat.get('um', '')

    y = ph - mt

    if ean:
        try:
            bar_h = min(14.0, etq_h * 0.42) * mm_unit
            bc = _bc_code128.Code128(ean, barHeight=bar_h, barWidth=0.9)
            scale = min(1.0, usable_w / bc.width) if bc.width > 0 else 1.0
            bw = bc.width * scale
            bh = bc.height * scale
            bx = x0 + (usable_w - bw) / 2
            by = y - bh
            c.saveState()
            c.translate(bx, by)
            c.scale(scale, scale)
            bc.drawOn(c, 0, 0)
            c.restoreState()
            y = by - 1.5 * mm_unit
            c.setFont('Helvetica', 7)
            c.drawCentredString(cx, y - 7, ean)
            y -= 7 + 2 * mm_unit
        except Exception:
            pass

    fs = 8
    c.setFont('Helvetica', fs)
    max_chars = max(1, int(usable_w / (fs * 0.52)))
    desc = descripcion[:max_chars] + ('...' if len(descripcion) > max_chars else '')
    y -= fs
    c.drawCentredString(cx, y, desc)
    y -= fs * 0.3 + 2 * mm_unit

    c.setFont('Helvetica-Bold', fs)
    code_um = f'{codigo}   UM: {um}' if um else codigo
    y -= fs
    c.drawCentredString(cx, y, code_um)


def generar_pdf_etiquetas_mateti(materiales: list[dict], cfg) -> str | None:
    """Genera un PDF con etiquetas de codigo de barras para materiales MATETI.

    Soporta multiples columnas por pagina. El ancho de pagina se calcula
    como columnas * ancho_etiqueta + separacion + margenes laterales.
    """
    try:
        etq_w_mm = cfg.ancho_etiqueta_mateti or 100.0
        etq_h_mm = cfg.alto_etiqueta_mateti or 150.0
        cols = max(1, cfg.columnas_etiqueta_mateti or 1)
        sep_mm = cfg.separacion_etiqueta_mateti or 0.0
        ml = (cfg.margen_izquierdo_etiquetas_mateti or 2.0) * mm_unit
        mr = (cfg.margen_derecho_etiquetas_mateti or 2.0) * mm_unit
        mt = (cfg.margen_superior_etiquetas_mateti or 2.0) * mm_unit

        etq_w = etq_w_mm * mm_unit
        etq_h = etq_h_mm * mm_unit
        sep = sep_mm * mm_unit

        pw = ml + cols * etq_w + (cols - 1) * sep + mr
        ph = etq_h + mt + (cfg.margen_inferior_etiquetas_mateti or 2.0) * mm_unit

        filename = f'mateti_{datetime.now().strftime("%Y%m%d-%H%M%S")}.pdf'
        filepath = os.path.join(_dir_etiquetas(), filename)
        c = canvas.Canvas(filepath, pagesize=(pw, ph))

        pendientes: list[dict] = []
        for mat in materiales:
            cantidad = max(1, int(mat.get('cantidad_etiquetas', 1)))
            for _ in range(cantidad):
                pendientes.append(mat)

        for i, mat in enumerate(pendientes):
            col_idx = i % cols
            x0 = ml + col_idx * (etq_w + sep)
            _dibujar_etiqueta_mateti(c, mat, x0, ph, mt, etq_w, etq_h_mm)
            if col_idx == cols - 1 or i == len(pendientes) - 1:
                c.showPage()

        c.save()
        return filepath
    except Exception:
        return None
