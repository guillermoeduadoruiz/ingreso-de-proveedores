# -*- coding: utf-8 -*-
"""Etiquetas en Direct Protocol (DP) para impresoras Honeywell/Intermec (PC42t).

La Honeywell PC42t soporta DP (Direct Protocol), el lenguaje nativo de
Honeywell/Intermec. Cuando la impresora de etiquetas configurada es una
Honeywell/PC42, la etiqueta NO se genera como PDF sino como un stream de
comandos DP que se envía por RAW a la cola de Windows (WritePrinter con
datatype "RAW").

Datos clave usados en el layout (WorkConfig: etiqueta 100x150 mm, 1x1):
- 203 dpi (PC42t "plus"): ~8 puntos/mm.
- QR Code vía BARSET "QRCODE", ratioW, ratioN, enlargement(module en dots),
  model (1/2), ECC (1-4). Se usa model=2 y ECC=4 (alta fiabilidad).
- Texto con fuentes escalables estándar "Swiss 721 BT" / "Swiss 721 Bold BT"
  (vienen en el firmware PC42t) y charset NASC 1252 (cp1252).
- Cada bulto imprime una única etiqueta física (sin duplicado apilado).
"""

from database.conexiones import ConfigImpresoras, ConfigImpresion
from modelos.ingreso import Ingreso
from reportlab.pdfbase.pdfmetrics import stringWidth

from servicios.pdf_generator import _fmt_num_remito

# ══════════════════════════════════════════════════════════════════════════
#  LAYOUT DE LA ETIQUETA  (editar acá para mover los grupos de campos)
# ══════════════════════════════════════════════════════════════════════════
#  Todas las medidas en mm, tomadas desde los bordes de la etiqueta:
#    *_X_MM → distancia desde el borde IZQUIERDO
#    *_Y_MM → distancia desde el borde SUPERIOR hasta la 1ª línea del grupo
#  Cada grupo se ubica en forma independiente: mover uno no desplaza a los
#  demás. Dentro de un grupo, las líneas se apilan hacia abajo a partir de
#  su *_Y_MM (interlineado = tamaño de fuente * 0.45 mm).
#  *_PT → tamaño de fuente (puntos enteros; la PC42t no acepta decimales).
# ──────────────────────────────────────────────────────────────────────────

# Tamaño de la etiqueta (se usa si la configuración no define ancho/alto).
# El PDF de etiquetas usa siempre estas medidas, para ser idéntico al DP.
ETQ_ANCHO_MM = 100.0
ETQ_ALTO_MM = 150.0
# Límite derecho para textos y guiones separadores: distancia al borde
# DERECHO de la etiqueta. Los textos que no entran se recortan con "...".
ETQ_MARGEN_DER_MM = 8.0
# Distancia mínima entre la parte superior de cualquier texto y el borde
# superior de la etiqueta. Si un texto sale de la etiqueta, la PC42t pierde
# el gap y da error (LED rojo) en la etiqueta siguiente. Con 1 mm el error
# pasó de la 2ª a después de la 3ª etiqueta (el desfase se acumula): la zona
# útil real es menor a 150 mm, por eso se deja más margen.
ETQ_TOPE_SUP_MM = 5.0

# 1) Título principal ("CUSPIDE SAU") + línea separadora debajo.
#    El título se centra horizontalmente sobre TITULO_CENTRO_X_MM.
TITULO_CENTRO_X_MM = 45.5
TITULO_Y_MM = 3.0
TITULO_PT = 18

# 2) Destinatario: Dest / Suc / Dom / CP-Ciudad / Distrito-Transporte.
DESTINATARIO_X_MM = 8.0
DESTINATARIO_Y_MM = 18.4
DESTINATARIO_PT = 10

# 3) Proveedor: nombre (PT, negrita) + "Fecha y Remito del proveedor" y su
#    valor (PT - 1).
PROVEEDOR_X_MM = 8.0
PROVEEDOR_Y_MM = 50.0
PROVEEDOR_PT = 9

# 4) Remitente: línea separadora + Rem (PT, negrita) + dirección y CUIT
#    (PT - 1).
REMITENTE_X_MM = 8.0
REMITENTE_Y_MM = 80.0
REMITENTE_PT = 9

# 5) Remito de Cross Docking ("Remito de Cross Docking: xxxxx-xxxxxxxx",
#    negrita). Número emitido por esta app.
REMITO_CD_X_MM = 8.0
REMITO_CD_Y_MM = 98.1
REMITO_CD_PT = 9

# 6) Órdenes de compra: "OC:" (negrita) + grilla de códigos. "OC:" ocupa la
#    1ª celda de la grilla. Si no entran todos los códigos, el último lugar
#    muestra "+N mas".
OC_X_MM = 8.0
OC_Y_MM = 101.3
OC_PT = 9
OC_ANCHO_MM = None      # ancho de la grilla (define cuántas columnas entran);
                        # None = hasta el límite derecho (ETQ_MARGEN_DER_MM)
OC_Y_MAX_MM = None      # límite inferior de la grilla (Y en mm); None = hasta
                        # 2 mm por encima del Muelle/QR (o 6 mm del pie sin QR)
                        # y, si el Remito CD está debajo de las OC, 2 mm por
                        # encima de él.

# 7) Muelle ("Muelle: xx").
MUELLE_X_MM = 8.0
MUELLE_Y_MM = 114.9
MUELLE_PT = 9

# 8) QR de trazabilidad: esquina superior izquierda en (QR_X_MM, QR_Y_MM).
#    QR_LADO_MM es el lado con que lo dibuja el PDF. En la PC42t el tamaño
#    impreso real lo fija QR_MODULO_DOTS (dots por módulo del QR) según la
#    cantidad de datos.
QR_X_MM = 10.0
QR_Y_MM = 143.0
QR_LADO_MM = 25.0
QR_MODULO_DOTS = 2

# ══════════════════════════════════════════════════════════════════════════
DPI = 203
_PT = DPI / 25.4  # puntos por mm (~8)
EMPRESA_TITULO = 'CUSPIDE SAU'

# Línea de separación dibujada como texto (guiones), sin depender de LO.
# El combo 30 guiones a 9pt está verificado en la PC42t (30@9 OK; 40@7 y
# 44@7/44@9 = LED rojo): cada comando PT lleva como máximo 30 guiones y la
# línea completa se arma con varios PT consecutivos hasta ETQ_MARGEN_DER_MM.
REGLA_PT = 9
REGLA_MAX_POR_PT = 30


def _dots(mm_val: float) -> int:
    return int(round(mm_val * _PT))


def _limpiar(texto: str) -> str:
    """Sanitiza texto para insertarlo como literal DP (dentro de comillas)."""
    if not texto:
        return ''
    return (
        (texto or '')
        .replace('\\', ' ')
        .replace('"', "'")
        .replace('\r', ' ')
        .replace('\n', ', ')
        .strip()
    )


def _em_dash_a_guion(texto: str) -> str:
    return (texto or '').replace('—', ' - ')


def _est_ancho_dots(texto: str, pt: int, bold: bool = False) -> int:
    """Ancho en dots de un texto Swiss 721 (proporcional).

    Reemplaza a AN 8/AN 9 para centrar/derecha-alinear: el firmware de la PC42t
    entra en error si un mismo label combina AN 8 y AN 9 (verificado: cada uno
    por separado imprime, juntos = LED rojo). Swiss 721 es un clon métrico de
    Helvetica, así que se usan las métricas de Helvetica de reportlab. La
    precisión importa: las líneas largas se arman con varios PT consecutivos
    ubicados según este ancho.
    """
    fuente = 'Helvetica-Bold' if bold else 'Helvetica'
    return _dots(stringWidth(texto, fuente, pt) * 25.4 / 72)


def _colectar_rps(destino: dict) -> str:
    vistos: set[str] = set()
    partes: list[str] = []
    for remito in destino.get('remitos', []):
        for rp in remito.recepciones:
            if rp.id_recepcion not in vistos:
                vistos.add(rp.id_recepcion)
                partes.append(rp.id_recepcion)
    return ', '.join(partes)


def _qr_data(ingreso, destino, rp_cliente, muelle_despacho, rps, fecha_str,
             remitente: ConfigImpresion) -> str:
    """Mismo payload exacto que el QR de pdf_generator (paridad de trazabilidad)."""
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
    return qr_data


def _esc_f(fuente: str, pt: int) -> str:
    return f'FT "{fuente}",{pt}'


_REG = 'Swiss 721 BT'
_BOLD = 'Swiss 721 Bold BT'

# Límite seguro de caracteres por comando PT en la PC42t. La impresora entra en
# modo error (LED rojo) con cadenas >= 44 chars (42 OK, 44 rojo). Las líneas
# más largas se parten en varios PT consecutivos (ver `_pt_largo`).
MAX_PT_LEN = 40


def _pb_expr(qr_data: str) -> str:
    """Convierte el payload QR en una expresión PB que respeta los saltos de línea.

    DP no permite CR literal dentro del dato de un bar code; se encoda como
    CHR$(13) separando los segmentos con ';' (sintaxis de PRBAR en DP).
    """
    partes = []
    for i, linea in enumerate((qr_data or '').split('\n')):
        if i:
            partes.append('CHR$(13)')
        partes.append(f'"{_limpiar(linea)}"')
    return ';'.join(partes)


def layout_etiqueta(
    ancho_mm: float, alto_mm: float, marg_t_mm: float, marg_r_mm: float,
    proveedor: str, nombre_destino: str, sucursal: str, rp_cliente,
    fecha_str: str, remitente: ConfigImpresion, codigos: list[str],
    qr_data: str, muelle_despacho: str, idx: int, total: int,
    remitos_prov_str: str = '', num_remito: str = '',
) -> list[tuple]:
    """Arma una etiqueta como lista de elementos, independiente del formato.

    Es la única fuente de la estructura de la etiqueta: DP (`_render_dp`) y
    PDF (`pdf_generator.generar_etiquetas`) dibujan exactamente estos
    elementos. Coordenadas en dots (203 dpi), `y` lógica desde el borde
    superior (0 = arriba, creciente = hacia abajo). Elementos:
      ('texto', x, y, texto, pt, bold, max_por_pt)  → texto ya recortado al ancho
      ('qr', x, y, data)                            → esquina superior izquierda
    """
    elems: list[tuple] = []
    x_max = _dots(ancho_mm - ETQ_MARGEN_DER_MM)

    def _texto(x: int, y: int, texto: str, pt: int, bold: bool = False,
               max_por_pt: int = MAX_PT_LEN):
        """Agrega un texto; si no entra hasta `x_max` se recorta con "..."."""
        texto = _limpiar(_em_dash_a_guion(texto))
        disponible = x_max - x
        if _est_ancho_dots(texto, pt, bold) > disponible:
            while texto and _est_ancho_dots(texto.rstrip() + '...', pt, bold) > disponible:
                texto = texto[:-1]
            texto = texto.rstrip() + '...'
        if texto:
            elems.append(('texto', x, y, texto, pt, bold, max_por_pt))

    class _Grupo:
        """Cursor de texto de un grupo: arranca en (x_mm, y_mm) y apila líneas."""

        def __init__(self, x_mm: float, y_mm: float):
            self.x = _dots(x_mm)
            self.y = _dots(y_mm)

        def linea(self, texto: str, pt: int, bold: bool = False):
            _texto(self.x, self.y, texto, pt, bold)
            self.y += _dots(pt * 0.45)

        def regla(self):
            """Guiones separadores desde x hasta ETQ_MARGEN_DER_MM."""
            guion = stringWidth('-', 'Helvetica', REGLA_PT) * 25.4 / 72 * _PT
            n = max(1, int((x_max - self.x) // guion))
            _texto(self.x, self.y, '-' * n, REGLA_PT, max_por_pt=REGLA_MAX_POR_PT)
            self.y += _dots(REGLA_PT * 0.45)

        def espacio(self, mm_val: float):
            self.y += _dots(mm_val)

    # ── 1) Título principal: centrado sobre TITULO_CENTRO_X_MM (sin AN) ──
    _t_ancho = _est_ancho_dots(EMPRESA_TITULO, TITULO_PT, bold=True)
    _texto(_dots(TITULO_CENTRO_X_MM) - _t_ancho // 2, _dots(TITULO_Y_MM),
           EMPRESA_TITULO, TITULO_PT, bold=True)
    # Línea separadora debajo del título, alineada con el destinatario.
    # +1.5 mm: en DP el título queda más bajo por ETQ_TOPE_SUP_MM.
    _Grupo(DESTINATARIO_X_MM, TITULO_Y_MM + TITULO_PT * 0.55 + 1.5).regla()

    # ── 2) Destinatario ──
    g = _Grupo(DESTINATARIO_X_MM, DESTINATARIO_Y_MM)
    pt = DESTINATARIO_PT
    g.linea(f'Dest: {nombre_destino}', pt, bold=True)
    g.linea(f'Suc: {sucursal}', pt)
    if rp_cliente:
        if rp_cliente.domicilio_cliente:
            g.linea(f'Dom: {rp_cliente.domicilio_cliente}', pt)
        if rp_cliente.codigo_postal_cliente or rp_cliente.ciudad_cliente:
            partes = []
            if rp_cliente.codigo_postal_cliente:
                partes.append(f'CP: {rp_cliente.codigo_postal_cliente}')
            if rp_cliente.ciudad_cliente:
                partes.append(f'Ciudad: {rp_cliente.ciudad_cliente}')
            g.linea(' - '.join(partes), pt)
        if rp_cliente.distrito_cliente:
            g.linea(f'Distrito: {rp_cliente.distrito_cliente}', pt)
        if rp_cliente.transporte_descripcion:
            g.linea(f'Trans: {rp_cliente.transporte_descripcion}', pt)

    # ── 3) Proveedor + fecha y remito del proveedor (título y valor en líneas
    #     separadas: el valor no entra junto al título en el ancho) ──
    g = _Grupo(PROVEEDOR_X_MM, PROVEEDOR_Y_MM)
    g.linea(f'Proveedor: {proveedor}', PROVEEDOR_PT, bold=True)
    g.linea('Fecha y Remito del proveedor:', PROVEEDOR_PT - 1, bold=True)
    valor_linea = fecha_str
    if remitos_prov_str:
        valor_linea += f' - {remitos_prov_str}'
    g.linea(valor_linea, PROVEEDOR_PT - 1)

    # ── 4) Remitente ──
    g = _Grupo(REMITENTE_X_MM, REMITENTE_Y_MM)
    g.regla()
    g.espacio(1.0)
    g.linea(f'Rem: {remitente.remitente_nombre}', REMITENTE_PT, bold=True)
    g.linea(f'{remitente.remitente_direccion} - {remitente.remitente_ciudad}', REMITENTE_PT - 1)
    g.linea(f'CUIT: {remitente.remitente_cuit}', REMITENTE_PT - 1)

    qx = _dots(QR_X_MM)
    qy = _dots(QR_Y_MM)
    my = _dots(MUELLE_Y_MM)

    # ── 5) Remito de Cross Docking: número emitido por esta app ──
    if num_remito:
        g = _Grupo(REMITO_CD_X_MM, REMITO_CD_Y_MM)
        g.linea(f'Remito de Cross Docking: {num_remito}', REMITO_CD_PT, bold=True)

    # ── 6) Órdenes de compra: grilla ──
    # Los códigos tienen todos el mismo largo, así las columnas se alinean
    # aunque la fuente sea proporcional (Swiss 721 BT, verificada en la PC42t).
    # ⚠️ No usar "Andale Mono" aquí: produjo error de impresora en la PC42t
    # (el job RAW falla si el firmware no encuentra esa fuente por ese nombre).
    g = _Grupo(OC_X_MM, OC_Y_MM)
    oc_font = OC_PT
    if codigos:
        codigos = [cod[2:] if cod.startswith('CU') else cod for cod in codigos]
        row_h_mm = (oc_font + 2) * 0.3528
        if OC_Y_MAX_MM is not None:
            limite = _dots(OC_Y_MAX_MM)
        elif qr_data:
            limite = (min(qy, my) if muelle_despacho else qy) - _dots(2)
        else:
            limite = _dots(alto_mm - 6.0)
        # Si el Remito CD quedó debajo de las OC, la grilla no lo pisa.
        if num_remito and REMITO_CD_Y_MM > OC_Y_MM:
            limite = min(limite, _dots(REMITO_CD_Y_MM) - _dots(2))
        avail_h = limite - g.y
        max_rows = max(1, int(avail_h // _dots(row_h_mm)) + 1)

        max_code_len = max((len(cod) for cod in codigos), default=3)
        col_w_mm = (max_code_len + 1) * (oc_font * 0.2117)
        oc_ancho_mm = OC_ANCHO_MM if OC_ANCHO_MM is not None else (x_max - g.x) / _PT
        max_cols = max(1, int(oc_ancho_mm // col_w_mm))
        max_items = max(1, max_rows * max_cols - 1)

        if len(codigos) > max_items:
            restantes = len(codigos) - (max_items - 1)
            codigos = codigos[:max(0, max_items - 1)] + [f'+{restantes} mas']

        _texto(g.x, g.y, 'OC:', oc_font, bold=True)
        for i, codigo in enumerate(codigos):
            slot = i + 1
            col = slot % max_cols
            row = slot // max_cols
            _texto(g.x + _dots(col * col_w_mm), g.y + _dots(row * row_h_mm), codigo, oc_font)

    if qr_data:
        # ── 8) QR: esquina superior izquierda en (QR_X_MM, QR_Y_MM) ──
        elems.append(('qr', qx, qy, qr_data))
        # ── 7) Muelle ──
        if muelle_despacho:
            g = _Grupo(MUELLE_X_MM, MUELLE_Y_MM)
            g.linea(f'Muelle: {muelle_despacho}', MUELLE_PT)

    # Contador de bulto (esquina inferior derecha).
    _ct = f'{idx}/{total}'
    elems.append((
        'texto', _dots(ancho_mm - marg_r_mm) - _est_ancho_dots(_ct, 11),
        _dots(alto_mm - marg_t_mm), _ct, 11, False, MAX_PT_LEN,
    ))
    return elems


def _render_dp(elems: list[tuple], alto_mm: float) -> list[str]:
    """Traduce los elementos de `layout_etiqueta` a comandos DP."""
    out: list[str] = []

    # Calibración (2026-09-22): la PC42t interpreta la fila de PP al revés
    # (y física grande = arriba de la etiqueta, y física chica = pie). Toda la
    # lógica trabaja con y "lógica" (0 = borde superior, creciente = hacia
    # abajo) y se espeja recién al emitir cada comando PP con `_yp`.
    def _yp(y_log: int) -> int:
        return _dots(alto_mm) - y_log

    # (2026-09-24) En la PC42t el campo PT crece hacia ARRIBA desde su PP
    # (ALIGN 1 = esquina inferior). Si la caja de un texto supera el alto de
    # la etiqueta, la imagen queda más larga que la etiqueta, la impresora
    # pierde el gap y entra en error (LED rojo) antes de la 2ª etiqueta del
    # job. Se limita el PP para que la caja termine a ETQ_TOPE_SUP_MM del borde.
    tope_sup = _dots(alto_mm - ETQ_TOPE_SUP_MM)

    for e in elems:
        if e[0] == 'qr':
            _, x, y, data = e
            out.append(
                f'PP {x},{_yp(y)}:BARSET "QRCODE",1,1,{QR_MODULO_DOTS},2,4:'
                f'PB {_pb_expr(data)}'
            )
            continue
        _, x, y, texto, pt, bold, max_por_pt = e
        # Líneas de más de `max_por_pt` caracteres: varios PT consecutivos
        # (cortando en un espacio cuando se puede), cada uno ubicado a
        # continuación del anterior según el ancho medido del texto previo.
        fuente = _esc_f(_BOLD if bold else _REG, pt)
        yp = max(0, min(_yp(y), tope_sup - _dots(pt * 25.4 / 72)))
        inicio = 0
        while inicio < len(texto):
            fin = min(len(texto), inicio + max_por_pt)
            if fin < len(texto):
                corte = texto.rfind(' ', inicio + 1, fin)
                if corte > inicio:
                    fin = corte + 1  # el espacio queda al final del trozo
            trozo = texto[inicio:fin].strip()
            if trozo:
                px = x + _est_ancho_dots(texto[:inicio], pt, bold)
                out.append(f'PP {px},{yp}:{fuente}:PT "{trozo}"')
            inicio = fin
    return out


def parametros_etiqueta(cfg: ConfigImpresoras) -> tuple[float, float, float, float]:
    """(ancho, alto, margen superior, margen derecho) en mm para el layout.

    La ubicación de los grupos de campos la definen las constantes de LAYOUT
    (al inicio del módulo). Los márgenes de la configuración solo ubican el
    contador de bulto (esquina inferior derecha).
    """
    return (
        cfg.ancho_etiqueta or ETQ_ANCHO_MM,
        cfg.alto_etiqueta or ETQ_ALTO_MM,
        cfg.margen_superior_etiquetas or 3.0,
        cfg.margen_derecho_etiquetas or 5.0,
    )


def generar_etiquetas_dp(
    ingreso: Ingreso,
    destino: dict,
    cfg: ConfigImpresoras,
    remitente: ConfigImpresion,
    num_remito: str = '',
) -> bytes:
    """Construye el stream DP completo (todas las etiquetas del destino)."""
    total = destino.get('total_bultos', 0) or 0
    if total <= 0:
        return b''

    fecha_str = ingreso.fecha_ingreso.strftime('%d/%m/%Y')
    rps = _colectar_rps(destino)
    rps_codigos = [c.strip() for c in rps.split(',') if c.strip()]

    remitos_prov: list[str] = []
    _vistos_rem_prov: set[str] = set()
    for rem in destino.get('remitos', []):
        if rem.num_remito and rem.num_remito not in _vistos_rem_prov:
            _vistos_rem_prov.add(rem.num_remito)
            remitos_prov.append(_fmt_num_remito(rem.num_remito))
    remitos_prov_str = ', '.join(remitos_prov)

    rp_cliente = None
    for rem in destino.get('remitos', []):
        if rem.recepciones:
            rp_cliente = rem.recepciones[0]
            break

    muelle_despacho = rp_cliente.transporte_datos_privados if rp_cliente else ''
    qr_data = ''
    if muelle_despacho:
        qr_data = _qr_data(
            ingreso, destino, rp_cliente, muelle_despacho,
            rps, fecha_str, remitente,
        )

    ancho_mm, alto_mm, marg_t_mm, marg_r_mm = parametros_etiqueta(cfg)

    lineas = ['NASC 1252']
    for idx in range(total):
        lineas.extend(_render_dp(layout_etiqueta(
            ancho_mm, alto_mm, marg_t_mm, marg_r_mm,
            ingreso.proveedor.descripcion,
            destino.get('destino', ''),
            destino.get('sucursal', ''),
            rp_cliente, fecha_str, remitente,
            rps_codigos, qr_data, muelle_despacho,
            idx + 1, total,
            remitos_prov_str, num_remito,
        ), alto_mm))
        lineas.append('PF')

    return ('\r\n'.join(lineas) + '\r\n').encode('cp1252', errors='replace')


def imprimir_etiquetas_dp(
    ingreso: Ingreso,
    destino: dict,
    cfg: ConfigImpresoras,
    remitente: ConfigImpresion,
    printer_name: str,
    num_remito: str = '',
) -> int:
    """Genera y envía el stream DP por RAW a la cola de Windows."""
    data = generar_etiquetas_dp(ingreso, destino, cfg, remitente, num_remito)
    if not data:
        return 0
    import win32print
    handle = win32print.OpenPrinter(printer_name)
    try:
        job = win32print.StartDocPrinter(
            handle, 1, ('etiquetas_direct_protocol', None, 'RAW')
        )
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, data)
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)
    return destino.get('total_bultos', 0) or 0