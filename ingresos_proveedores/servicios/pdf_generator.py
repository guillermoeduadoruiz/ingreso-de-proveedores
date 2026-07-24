import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib.units import mm as mm_unit
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
)
from reportlab.pdfgen import canvas
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from modelos.ingreso import Ingreso
from database.conexiones import ConfigImpresion, ConfigImpresoras
from utils.paths import pdfs_dir as _pdfs_dir, assets_dir as _assets_dir


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


def generar_remito(
    ingreso: Ingreso,
    destino: dict,
    remitente: ConfigImpresion,
    cfg: ConfigImpresoras,
    num_remito: str,
) -> str:
    filename = f'{num_remito}.pdf'
    filepath = os.path.join(_dir_remitos(), filename)

    page_w, page_h = A4
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        topMargin=_mm(cfg.margen_superior_remitos), bottomMargin=_mm(cfg.margen_inferior_remitos),
        leftMargin=_mm(cfg.margen_izquierdo_remitos), rightMargin=_mm(cfg.margen_derecho_remitos),
    )
    styles = getSampleStyleSheet()
    available_w = page_w - _mm(cfg.margen_izquierdo_remitos + cfg.margen_derecho_remitos)

    s_empresa = ParagraphStyle('Empresa', parent=styles['Normal'], fontSize=14, leading=17,
                               alignment=TA_CENTER, fontName='Helvetica-Bold')
    s_datos_empresa = ParagraphStyle('DatosEmpresa', parent=styles['Normal'], fontSize=8, leading=10,
                                     alignment=TA_CENTER, textColor=colors.HexColor('#444444'))
    s_remito_num = ParagraphStyle('RemitoNum', parent=styles['Normal'], fontSize=20, leading=24,
                                  alignment=TA_CENTER, fontName='Helvetica-Bold',
                                  textColor=colors.HexColor('#1565C0'))
    s_section = ParagraphStyle('Section', parent=styles['Normal'], fontSize=9, leading=11,
                               fontName='Helvetica-Bold', textColor=colors.HexColor('#333333'))
    s_normal = ParagraphStyle('Normal2', parent=styles['Normal'], fontSize=9, leading=12)
    s_normal_bold = ParagraphStyle('NormalBold', parent=styles['Normal'], fontSize=9, leading=12,
                                   fontName='Helvetica-Bold')
    s_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=7, leading=9,
                             textColor=colors.HexColor('#666666'))
    s_firma = ParagraphStyle('Firma', parent=styles['Normal'], fontSize=9, leading=12,
                             alignment=TA_CENTER)
    s_firma_label = ParagraphStyle('FirmaLabel', parent=styles['Normal'], fontSize=8, leading=10,
                                   alignment=TA_CENTER, textColor=colors.HexColor('#666666'))

    elements = []

    # ── ENCABEZADO: Logo + Datos de la empresa ──
    logo_path = os.path.join(_assets_dir(), 'logo-cuspide.jpg')
    logo_w = _mm(30)
    logo_h = _mm(30)
    if os.path.exists(logo_path):
        logo_img = Image(logo_path, width=logo_w, height=logo_h)
        logo_img.hAlign = 'LEFT'
    else:
        logo_img = Paragraph('', s_normal)

    company_col_w = available_w - logo_w - _mm(6)
    header_data = [
        [
            logo_img,
            Paragraph(
                f'<b>{remitente.remitente_nombre}</b><br/>'
                f'{remitente.remitente_direccion} — {remitente.remitente_ciudad}<br/>'
                f'CUIT: {remitente.remitente_cuit}  |  Tel: {remitente.remitente_telefono}',
                s_datos_empresa
            ),
        ],
    ]
    t_header = Table(header_data, colWidths=[logo_w + _mm(4), company_col_w])
    t_header.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#1565C0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (0, 0), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E3F2FD')),
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 4 * mm_unit))

    # ── TITULO REMITO ──
    elements.append(Paragraph(f'REMITO N° {num_remito}', s_remito_num))
    elements.append(Spacer(1, 4 * mm_unit))

    # ── REMITENTE / DESTINATARIO lado a lado ──
    col_w = available_w / 2 - _mm(2)
    remitente_data = [
        [Paragraph('<b>REMITENTE</b>', s_section)],
        [Paragraph(
            f'{remitente.remitente_nombre}<br/>'
            f'{remitente.remitente_direccion}<br/>'
            f'{remitente.remitente_ciudad}<br/>'
            f'CUIT: {remitente.remitente_cuit}',
            s_small
        )],
    ]
    t_rem = Table(remitente_data, colWidths=[col_w])
    t_rem.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#999999')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8E8E8')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))

    # ── Obtener datos del cliente desde las recepciones ──
    rp_cliente = None
    for rem in destino.get('remitos', []):
        if rem.recepciones:
            rp_cliente = rem.recepciones[0]
            break

    destino_lines = [f'{destino["destino"]}', f'Sucursal: {destino["sucursal"]}']
    if rp_cliente:
        if rp_cliente.domicilio_cliente:
            destino_lines.append(f'Dom: {rp_cliente.domicilio_cliente}')
        if rp_cliente.codigo_postal_cliente:
            destino_lines.append(f'CP: {rp_cliente.codigo_postal_cliente}')
        if rp_cliente.ciudad_cliente:
            destino_lines.append(f'Ciudad: {rp_cliente.ciudad_cliente}')
        if rp_cliente.distrito_cliente:
            destino_lines.append(f'Distrito: {rp_cliente.distrito_cliente}')
        if rp_cliente.transporte_descripcion:
            destino_lines.append(f'Transporte: {rp_cliente.transporte_descripcion}')
        if rp_cliente.transporte_datos_privados:
            destino_lines.append(f'Muelle de despacho: {rp_cliente.transporte_datos_privados}')

    destino_data = [
        [Paragraph('<b>DESTINATARIO</b>', s_section)],
        [Paragraph('<br/>'.join(destino_lines), s_small)],
    ]
    t_dest = Table(destino_data, colWidths=[col_w])
    t_dest.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#999999')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8E8E8')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))

    t_lado_a_lado = Table(
        [[t_rem, t_dest]],
        colWidths=[col_w + _mm(2), col_w + _mm(2)],
    )
    t_lado_a_lado.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(t_lado_a_lado)
    elements.append(Spacer(1, 4 * mm_unit))

    # ── FECHA E INGRESO ──
    elements.append(Paragraph(
        f'<b>Fecha de Ingreso:</b> {ingreso.fecha_ingreso.strftime("%d/%m/%Y")} '
        f'&nbsp;&nbsp;&nbsp; '
        f'<b>ID Ingreso:</b> {ingreso.id_ingreso}',
        s_normal
    ))
    elements.append(Spacer(1, 3 * mm_unit))

    # ── RECEPCIONES PREVISTAS ASOCIADAS ──
    rps = _colectar_rps(destino)
    if rps:
        elements.append(Paragraph(f'<b>Recepciones Previstas:</b> {rps}', s_small))
        elements.append(Spacer(1, 2 * mm_unit))

    # ── PROVEEDOR ──
    sucursal_corta = destino['sucursal']
    if sucursal_corta.upper().startswith('CCU'):
        sucursal_corta = sucursal_corta[3:]
    elements.append(Paragraph(
        f'<b>Proveedor:</b> {ingreso.proveedor.num_proveedor} — '
        f'{ingreso.proveedor.descripcion}  '
        f'<b>CU:</b> {sucursal_corta}',
        s_small
    ))
    elements.append(Spacer(1, 4 * mm_unit))

    # ── TABLA DE REMITOS ──
    remitos_grupo = destino.get('remitos', [])
    total_unidades = sum(rem.cantidad_unidades for rem in remitos_grupo)
    total_valor_declarado = sum(rem.valor_declarado_total for rem in remitos_grupo)

    tiene_unidades = any(rem.cantidad_unidades > 0 for rem in remitos_grupo)
    if tiene_unidades:
        header_row = ['N° Remito', 'Fecha', 'Bultos', 'Unid.', 'V. Decl. Unit.', 'Total V. Decl.']
        data_table = [header_row]
        for rem in remitos_grupo:
            vd_unit = rem.valor_declarado_unitario
            vd_total = rem.valor_declarado_total
            data_table.append([
                rem.num_remito,
                rem.fecha_remito.strftime('%d/%m/%Y'),
                str(rem.cantidad_bultos),
                str(rem.cantidad_unidades),
                f'${vd_unit:,.2f}' if vd_unit > 0 else '-',
                f'${vd_total:,.2f}' if vd_total > 0 else '-',
            ])
        total_line = ['TOTAL', '', str(destino['total_bultos']), str(total_unidades),
                      '', f'${total_valor_declarado:,.2f}' if total_valor_declarado > 0 else '']
        data_table.append(total_line)
        col_widths = [_mm(35), _mm(28), _mm(22), _mm(20), _mm(32), _mm(32)]
        align_right = (2, 3, 4, 5)
    else:
        header_row = ['N° Remito', 'Fecha', 'Bultos']
        data_table = [header_row]
        for rem in remitos_grupo:
            data_table.append([
                rem.num_remito,
                rem.fecha_remito.strftime('%d/%m/%Y'),
                str(rem.cantidad_bultos),
            ])
        data_table.append(['TOTAL', '', str(destino['total_bultos'])])
        col_widths = [_mm(50), _mm(40), _mm(35)]
        align_right = (2,)

    t_table = Table(data_table, colWidths=col_widths)
    style_cmds = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#333333')),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#BBBBBB')),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E3F2FD')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F5F5F5')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#333333')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]
    for ac in align_right:
        style_cmds.append(('ALIGN', (ac, 0), (ac, -1), 'RIGHT'))
    style_cmds.append(('ALIGN', (0, 0), (0, -1), 'LEFT'))
    t_table.setStyle(TableStyle(style_cmds))
    elements.append(t_table)

    # ── TOTAL VALOR DECLARADO ──
    if total_valor_declarado > 0:
        elements.append(Spacer(1, 4 * mm_unit))
        s_vd = ParagraphStyle('VD', parent=styles['Normal'], fontSize=12, leading=16,
                              fontName='Helvetica-Bold', alignment=TA_RIGHT)
        elements.append(Paragraph(
            f'TOTAL VALOR DECLARADO: ${total_valor_declarado:,.2f}', s_vd
        ))

    # ── FIRMAS ──
    elements.append(Spacer(1, 15 * mm_unit))

    sig_w = available_w / 2 - _mm(10)
    firmas_data = [
        [
            Paragraph('___________________________________', s_firma),
            Paragraph('___________________________________', s_firma),
        ],
        [
            Paragraph('Firma y Aclaración Remitente', s_firma_label),
            Paragraph('Firma y Aclaración Recepcionista', s_firma_label),
        ],
    ]
    t_firmas = Table(firmas_data, colWidths=[sig_w, sig_w])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_firmas)

    # ── PIE ──
    elements.append(Spacer(1, 8 * mm_unit))
    s_pie = ParagraphStyle('Pie', parent=styles['Normal'], fontSize=7, leading=9,
                           alignment=TA_CENTER, textColor=colors.HexColor('#999999'))
    elements.append(Paragraph(
        f'{remitente.remitente_nombre} — Documento generado automáticamente — {num_remito}',
        s_pie
    ))

    doc.build(elements)
    return filepath


def generar_etiquetas(
    ingreso: Ingreso,
    destino: dict,
    cfg: ConfigImpresoras,
    remitente: ConfigImpresion,
) -> str:
    label_w = _mm(cfg.ancho_etiqueta)
    label_h = _mm(cfg.alto_etiqueta)
    cols = cfg.columnas_etiqueta
    rows = cfg.filas_etiqueta
    labels_per_page = cols * rows
    total = destino['total_bultos']
    num_pages = max(1, (total + labels_per_page - 1) // labels_per_page)

    page_w = label_w * cols
    page_h = label_h * rows

    rps = _colectar_rps(destino)
    fecha_str = ingreso.fecha_ingreso.strftime('%d/%m/%Y')

    rp_cliente = None
    for rem in destino.get('remitos', []):
        if rem.recepciones:
            rp_cliente = rem.recepciones[0]
            break

    muelle_despacho = rp_cliente.transporte_datos_privados if rp_cliente else ''

    filename = f'{ingreso.id_ingreso}_{destino["sucursal"]}_etiquetas.pdf'
    filepath = os.path.join(_dir_etiquetas(), filename)

    c = canvas.Canvas(filepath, pagesize=(page_w, page_h))
    label_idx = 0

    for page in range(num_pages):
        for row in range(rows):
            for col in range(cols):
                if label_idx >= total:
                    continue
                x = col * label_w
                y = page_h - (row + 1) * label_h
                margin = 2
                font_size = 5

                c.rect(x, y, label_w, label_h, stroke=1, fill=0)

                text_w = label_w * 0.55
                qr_zone_x = x + text_w
                qr_zone_w = label_w - text_w

                line = y + label_h - margin - 7

                c.setFont('Helvetica-Bold', 6.5)
                c.drawString(x + margin, line, ingreso.proveedor.descripcion)

                line -= 7
                c.setFont('Helvetica-Bold', font_size)
                c.drawString(x + margin, line, f'Dest: {destino["destino"]}')
                line -= 6.5
                c.setFont('Helvetica', font_size)
                c.drawString(x + margin, line, f'Suc: {destino["sucursal"]}')

                line -= 6.5
                if rp_cliente:
                    if rp_cliente.domicilio_cliente:
                        c.drawString(x + margin, line, f'Dom: {rp_cliente.domicilio_cliente}')
                        line -= 6.5
                    if rp_cliente.codigo_postal_cliente or rp_cliente.ciudad_cliente:
                        parts = []
                        if rp_cliente.codigo_postal_cliente:
                            parts.append(f'CP: {rp_cliente.codigo_postal_cliente}')
                        if rp_cliente.ciudad_cliente:
                            parts.append(f'Ciudad: {rp_cliente.ciudad_cliente}')
                        c.drawString(x + margin, line, ' — '.join(parts))
                        line -= 6.5
                    if rp_cliente.distrito_cliente:
                        c.drawString(x + margin, line, f'Distrito: {rp_cliente.distrito_cliente}')
                        line -= 6.5
                    if rp_cliente.transporte_descripcion:
                        c.drawString(x + margin, line, f'Trans: {rp_cliente.transporte_descripcion}')
                        line -= 6.5

                c.setFont('Helvetica', font_size)
                if rps:
                    c.drawString(x + margin, line, f'RP: {rps}')
                    line -= 6.5
                c.drawString(x + margin, line, f'Fecha: {fecha_str}')

                line -= 6.5
                c.setFont('Helvetica-Bold', font_size)
                c.drawString(x + margin, line, f'Rem: {remitente.remitente_nombre}')

                line -= 6.5
                c.setFont('Helvetica', 4)
                c.drawString(x + margin, line, f'{remitente.remitente_direccion} — {remitente.remitente_ciudad}')
                line -= 5.5
                c.drawString(x + margin, line, f'CUIT: {remitente.remitente_cuit}')

                if muelle_despacho:
                    qr_data = (
                        f'Proveedor: {ingreso.proveedor.descripcion}\n'
                        f'Destino: {destino["destino"]}\n'
                        f'Sucursal: {destino["sucursal"]}\n'
                    )
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

                    qr_size = qr_zone_w - margin * 2
                    qr_x = qr_zone_x + (qr_zone_w - qr_size) / 2
                    qr_y = y + (label_h - qr_size) / 2

                    qr = QrCodeWidget(qr_data)
                    qr.barWidth = qr_size
                    qr.barHeight = qr_size
                    d = Drawing(qr_size, qr_size)
                    d.add(qr)
                    d.drawOn(c, qr_x, qr_y)

                    c.setFont('Helvetica', 3.5)
                    c.drawCentredString(
                        qr_zone_x + qr_zone_w / 2, qr_y - 4,
                        f'Muelle: {muelle_despacho}'
                    )

                c.setFont('Helvetica-Bold', 7)
                c.drawRightString(x + label_w - margin, y + margin, f'{label_idx + 1}/{total}')
                label_idx += 1
        if label_idx >= total:
            break
        c.showPage()

    c.save()
    return filepath
