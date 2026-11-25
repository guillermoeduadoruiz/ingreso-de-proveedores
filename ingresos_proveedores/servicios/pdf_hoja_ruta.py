"""PDF de la hoja de ruta: listado de remitos a despachar agrupado por destinatario.

Es un informe A4 en hoja blanca (no usa el preimpreso del remito), por eso se
abre con el visor de PDF en vez de mandarse a la impresora de remitos.
"""
import os
import time
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether,
)

from modelos.hoja_ruta import HojaRuta, agrupar_por_transporte
from utils.paths import pdfs_dir, assets_dir

AZUL = colors.HexColor('#1565C0')
GRIS = colors.HexColor('#EEEEEE')
GRIS_LINEA = colors.HexColor('#9E9E9E')
CELESTE = colors.HexColor('#E3F2FD')


def _dir_hojas_ruta() -> str:
    p = os.path.join(pdfs_dir(), 'hojas_ruta')
    os.makedirs(p, exist_ok=True)
    return p


def _p(texto, estilo) -> Paragraph:
    return Paragraph(escape('' if texto is None else str(texto)), estilo)


def _fecha(valor, con_hora: bool = False) -> str:
    if not valor:
        return ''
    return valor.strftime('%d/%m/%Y %H:%M' if con_hora else '%d/%m/%Y')


def _estilos():
    base = getSampleStyleSheet()
    return {
        'normal': ParagraphStyle('hr_normal', parent=base['Normal'], fontSize=8.5, leading=10.5),
        'chico': ParagraphStyle('hr_chico', parent=base['Normal'], fontSize=7.5, leading=9,
                                textColor=colors.HexColor('#424242')),
        'titulo': ParagraphStyle('hr_titulo', parent=base['Title'], fontSize=16, leading=19,
                                 alignment=TA_RIGHT, spaceAfter=0),
        'subtitulo': ParagraphStyle('hr_sub', parent=base['Normal'], fontSize=9, alignment=TA_RIGHT),
        'seccion': ParagraphStyle('hr_seccion', parent=base['Heading2'], fontSize=11, leading=13,
                                  textColor=AZUL, spaceBefore=4, spaceAfter=3),
        'dest': ParagraphStyle('hr_dest', parent=base['Normal'], fontSize=10, leading=12,
                               textColor=colors.white, fontName='Helvetica-Bold'),
        'th': ParagraphStyle('hr_th', parent=base['Normal'], fontSize=8, leading=10,
                             fontName='Helvetica-Bold'),
        'centro': ParagraphStyle('hr_centro', parent=base['Normal'], fontSize=8.5, alignment=TA_CENTER),
        'th_centro': ParagraphStyle('hr_th_centro', parent=base['Normal'], fontSize=8, leading=10,
                                    fontName='Helvetica-Bold', alignment=TA_CENTER),
        'transporte': ParagraphStyle('hr_transp', parent=base['Normal'], fontSize=11, leading=13,
                                     textColor=AZUL, fontName='Helvetica-Bold'),
        'transporte_der': ParagraphStyle('hr_transp_der', parent=base['Normal'], fontSize=8.5,
                                         leading=10, textColor=AZUL, alignment=TA_RIGHT),
    }


def _encabezado(hoja: HojaRuta, st) -> list:
    logo_path = os.path.join(assets_dir(), 'logo-cuspide.jpg')
    logo = Image(logo_path, width=45 * mm, height=15 * mm, kind='proportional') \
        if os.path.exists(logo_path) else Spacer(45 * mm, 15 * mm)
    derecha = [
        Paragraph(f'HOJA DE RUTA N° {hoja.numero}', st['titulo']),
        Paragraph(f'Fecha de despacho: <b>{_fecha(hoja.fecha_despacho)}</b> — '
                  f'Estado: <b>{escape(hoja.descripcion_estado)}</b>', st['subtitulo']),
    ]
    t = Table([[logo, derecha]], colWidths=[60 * mm, 120 * mm])
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('LINEBELOW', (0, 0), (-1, 0), 1.2, AZUL),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    return [t, Spacer(1, 4 * mm)]


def _datos_transporte(hoja: HojaRuta, destinatarios: list[dict], st) -> list:
    n_rem = sum(len(d['remitos']) for d in destinatarios)
    filas = [
        [_p('Transportista:', st['th']), _p(hoja.transportista, st['normal']),
         _p('Destinatarios:', st['th']), _p(len(destinatarios), st['normal'])],
        [_p('Chofer:', st['th']), _p(hoja.chofer, st['normal']),
         _p('Remitos:', st['th']), _p(n_rem, st['normal'])],
        [_p('Patente:', st['th']), _p(hoja.patente, st['normal']),
         _p('Bultos:', st['th']), _p(hoja.total_bultos, st['normal'])],
    ]
    if hoja.observaciones:
        filas.append([_p('Observaciones:', st['th']), _p(hoja.observaciones, st['normal']), '', ''])
    t = Table(filas, colWidths=[28 * mm, 82 * mm, 28 * mm, 42 * mm])
    estilo = [('BOX', (0, 0), (-1, -1), 0.6, GRIS_LINEA),
              ('BACKGROUND', (0, 0), (0, -1), GRIS),
              ('BACKGROUND', (2, 0), (2, 2), GRIS),
              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]
    if hoja.observaciones:
        estilo.append(('SPAN', (1, 3), (3, 3)))
    t.setStyle(TableStyle(estilo))
    return [t, Spacer(1, 5 * mm)]


def _resumen(transportes: list[dict], st) -> list:
    filas = [[_p('#', st['th']), _p('Destinatario', st['th']), _p('Domicilio', st['th']),
              _p('Remitos', st['th']), _p('Bultos', st['th'])]]
    estilo = [('BACKGROUND', (0, 0), (-1, 0), GRIS),
              ('GRID', (0, 0), (-1, -1), 0.4, GRIS_LINEA),
              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]
    i = 0
    for t in transportes:
        fila = len(filas)
        filas.append([Paragraph(f"Transporte: {escape(t['transporte'])}", st['th']), '', '',
                      _p(t['cantidad_remitos'], st['th_centro']),
                      _p(t['total_bultos'], st['th_centro'])])
        estilo += [('SPAN', (0, fila), (2, fila)), ('BACKGROUND', (0, fila), (-1, fila), CELESTE)]
        for d in t['destinatarios']:
            i += 1
            dom = ', '.join(x for x in (d['domicilio'], d['ciudad']) if x)
            filas.append([_p(i, st['centro']), _p(f"{d['nombre']} ({d['sucursal']})", st['normal']),
                          _p(dom, st['normal']), _p(len(d['remitos']), st['centro']),
                          _p(d['total_bultos'], st['centro'])])
    tabla = Table(filas, colWidths=[8 * mm, 72 * mm, 68 * mm, 16 * mm, 16 * mm], repeatRows=1)
    tabla.setStyle(TableStyle(estilo))
    return [Paragraph('Resumen por transporte y destinatario', st['seccion']), tabla, Spacer(1, 6 * mm)]


def _titulo_transporte(t: dict, st) -> Table:
    n_dest = len(t['destinatarios'])
    titulo = Table([[Paragraph(f"TRANSPORTE: {escape(t['transporte'])}", st['transporte']),
                     Paragraph(f"{n_dest} destinatario(s) — {t['cantidad_remitos']} remito(s) — "
                               f"{t['total_bultos']} bulto(s)", st['transporte_der'])]],
                   colWidths=[110 * mm, 70 * mm])
    titulo.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), CELESTE),
                                ('LINEABOVE', (0, 0), (-1, 0), 1.2, AZUL),
                                ('LINEBELOW', (0, 0), (-1, 0), 1.2, AZUL),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('TOPPADDING', (0, 0), (-1, -1), 4),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
    return titulo


def _bloque_destinatario(i: int, d: dict, st) -> list:
    titulo = Table([[Paragraph(f"{i}. {escape(d['nombre'] or d['sucursal'])} — "
                               f"Destino {escape(d['sucursal'])}", st['dest'])]],
                   colWidths=[180 * mm])
    titulo.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), AZUL)]))

    direccion = ' — '.join(x for x in (
        d['domicilio'],
        ' '.join(x for x in (d['codigo_postal'], d['ciudad']) if x),
        d['distrito'],
    ) if x)
    lineas = []
    if direccion:
        lineas.append(f'<b>Domicilio:</b> {escape(direccion)}')
    info = Paragraph('&nbsp;&nbsp;&nbsp;'.join(lineas) or '&nbsp;', st['chico'])

    filas = [[_p('N° Remito', st['th']), _p('ID Ingreso', st['th']), _p('Fecha Ingreso', st['th']),
              _p('Proveedor', st['th']), _p('Bultos', st['th'])]]
    for r in d['remitos']:
        prov = f"{r.get('num_proveedor') or ''} - {r.get('razon_social') or ''}".strip(' -')
        filas.append([_p(r.get('num_remito'), st['normal']), _p(r.get('id_ingreso'), st['normal']),
                      _p(_fecha(r.get('fecha_ingreso')), st['normal']), _p(prov, st['normal']),
                      _p(r.get('total_bultos') or 0, st['centro'])])
    filas.append(['', '', '', _p('Total destinatario', st['th']),
                  Paragraph(f"<b>{d['total_bultos']}</b>", st['centro'])])
    tabla = Table(filas, colWidths=[32 * mm, 30 * mm, 22 * mm, 80 * mm, 16 * mm], repeatRows=1)
    tabla.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), GRIS),
                               ('GRID', (0, 0), (-1, -2), 0.4, GRIS_LINEA),
                               ('BOX', (3, -1), (-1, -1), 0.4, GRIS_LINEA),
                               ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))

    firma = Table([[_p('Recibí conforme — Firma:', st['chico']), '',
                    _p('Aclaración:', st['chico']), '', _p('Fecha / Hora:', st['chico']), '']],
                  colWidths=[36 * mm, 34 * mm, 18 * mm, 38 * mm, 22 * mm, 32 * mm],
                  rowHeights=[12 * mm])
    firma.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
                               ('LINEBELOW', (1, 0), (1, 0), 0.5, colors.black),
                               ('LINEBELOW', (3, 0), (3, 0), 0.5, colors.black),
                               ('LINEBELOW', (5, 0), (5, 0), 0.5, colors.black)]))
    return [KeepTogether([titulo, Spacer(1, 1 * mm), info, Spacer(1, 1.5 * mm), tabla, firma]),
            Spacer(1, 6 * mm)]


def _firmas_finales(st) -> list:
    t = Table([['', '', ''], [_p('Firma despachante', st['centro']), '',
                              _p('Firma chofer / transportista', st['centro'])]],
              colWidths=[70 * mm, 40 * mm, 70 * mm], rowHeights=[16 * mm, None])
    t.setStyle(TableStyle([('LINEBELOW', (0, 0), (0, 0), 0.5, colors.black),
                           ('LINEBELOW', (2, 0), (2, 0), 0.5, colors.black)]))
    return [Spacer(1, 6 * mm), KeepTogether([t])]


def generar_pdf_hoja_ruta(hoja: HojaRuta) -> str:
    """Genera el PDF de la hoja de ruta y devuelve su ruta."""
    st = _estilos()
    destinatarios = hoja.destinatarios

    nombre = f'HR_{hoja.numero}.pdf'
    path = os.path.join(_dir_hojas_ruta(), nombre)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            # Probablemente abierto en el visor: generar con otro nombre.
            path = os.path.join(_dir_hojas_ruta(), f'HR_{hoja.numero}_{int(time.time())}.pdf')

    generado = datetime.now().strftime('%d/%m/%Y %H:%M')

    def _pie(canv, doc):
        canv.saveState()
        canv.setFont('Helvetica', 7.5)
        canv.setFillColor(colors.HexColor('#616161'))
        canv.drawString(15 * mm, 9 * mm, f'Hoja de Ruta N° {hoja.numero} — generada {generado}')
        canv.drawRightString(A4[0] - 15 * mm, 9 * mm, f'Página {doc.page}')
        canv.restoreState()

    doc = SimpleDocTemplate(
        path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=12 * mm, bottomMargin=16 * mm,
        title=f'Hoja de Ruta {hoja.numero}', author='Cuspide Libros',
    )
    story = []
    story += _encabezado(hoja, st)
    story += _datos_transporte(hoja, destinatarios, st)
    transportes = agrupar_por_transporte(hoja.remitos)
    story += _resumen(transportes, st)
    story.append(Paragraph('Detalle por transporte y destinatario', st['seccion']))
    i = 0
    for t in transportes:
        for j, d in enumerate(t['destinatarios']):
            i += 1
            bloque = _bloque_destinatario(i, d, st)
            if j == 0:
                # El título del transporte no queda solo al pie de una página.
                # (se aplana: un KeepTogether anidado salta de página aunque haya lugar)
                bloque[0] = KeepTogether([_titulo_transporte(t, st), Spacer(1, 2 * mm)]
                                         + list(bloque[0]._content))
            story += bloque
    story += _firmas_finales(st)
    doc.build(story, onFirstPage=_pie, onLaterPages=_pie)
    return path
