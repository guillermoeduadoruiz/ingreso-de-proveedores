from dataclasses import dataclass, field
from datetime import date, datetime

# Estados de la hoja de ruta
HR_EN_PREPARACION = 1
HR_DESPACHADA = 2
HR_ANULADA = 9
ESTADOS_HOJA = {
    HR_EN_PREPARACION: 'En preparación',
    HR_DESPACHADA: 'Despachada',
    HR_ANULADA: 'Anulada',
}

# Estados del remito generado (ingresoscd_remitos_generados.estado)
ESTADOS_REMITO = {1: 'Emitido', 2: 'En Muelle', 3: 'Despachado'}


@dataclass
class HojaRuta:
    fecha_despacho: date
    transportista: str = ''
    chofer: str = ''
    patente: str = ''
    observaciones: str = ''
    estado: int = HR_EN_PREPARACION
    id_hoja: int | None = None
    creado: datetime | None = None
    despachado: datetime | None = None
    # Filas de remitos generados (dicts de MySQLConnection._sql_detalle_remitos_generados)
    remitos: list[dict] = field(default_factory=list)

    @property
    def numero(self) -> str:
        return f'{self.id_hoja:06d}' if self.id_hoja else '(nueva)'

    @property
    def descripcion_estado(self) -> str:
        return ESTADOS_HOJA.get(self.estado, str(self.estado))

    @property
    def destinatarios(self) -> list[dict]:
        return agrupar_por_destinatario(self.remitos)

    @property
    def total_bultos(self) -> int:
        return sum(int(r.get('total_bultos') or 0) for r in self.remitos)

    @classmethod
    def desde_fila(cls, row: dict, remitos: list[dict] | None = None) -> 'HojaRuta':
        return cls(
            fecha_despacho=row['fecha_despacho'],
            transportista=row.get('transportista') or '',
            chofer=row.get('chofer') or '',
            patente=row.get('patente') or '',
            observaciones=row.get('observaciones') or '',
            estado=int(row.get('estado') or HR_EN_PREPARACION),
            id_hoja=row['id_hoja'],
            creado=row.get('creado'),
            despachado=row.get('despachado'),
            remitos=list(remitos or []),
        )


def agrupar_por_destinatario(remitos: list[dict]) -> list[dict]:
    """Agrupa filas de remitos generados por sucursal destino, ordenadas por nombre."""
    grupos: dict[str, dict] = {}
    for r in remitos:
        suc = r.get('sucursal_destino') or '(sin destino)'
        g = grupos.get(suc)
        if g is None:
            g = grupos[suc] = {
                'sucursal': suc,
                'nombre': r.get('nombre_destino') or '',
                'domicilio': r.get('domicilio_cliente') or '',
                'codigo_postal': r.get('codigo_postal_cliente') or '',
                'ciudad': r.get('ciudad_cliente') or '',
                'distrito': r.get('distrito_cliente') or '',
                'transporte': r.get('transporte_descripcion') or '',
                'remitos': [],
                'total_bultos': 0,
            }
        for clave, col in (('nombre', 'nombre_destino'), ('domicilio', 'domicilio_cliente'),
                           ('codigo_postal', 'codigo_postal_cliente'), ('ciudad', 'ciudad_cliente'),
                           ('distrito', 'distrito_cliente'), ('transporte', 'transporte_descripcion')):
            if not g[clave] and r.get(col):
                g[clave] = r[col]
        g['remitos'].append(r)
        g['total_bultos'] += int(r.get('total_bultos') or 0)
    for g in grupos.values():
        g['remitos'].sort(key=lambda r: str(r.get('num_remito') or ''))
    # Orden: por transporte (los que no tienen transporte al final) y dentro por destinatario.
    return sorted(grupos.values(), key=lambda g: (
        not g['transporte'], g['transporte'].lower(),
        (g['nombre'] or g['sucursal']).lower(), g['sucursal'],
    ))


SIN_TRANSPORTE = '(sin transporte)'


def agrupar_por_transporte(remitos: list[dict]) -> list[dict]:
    """Agrupa remitos por transporte del destinatario y, dentro, por destinatario."""
    grupos: dict[str, dict] = {}
    for d in agrupar_por_destinatario(remitos):
        nombre = d['transporte'] or SIN_TRANSPORTE
        g = grupos.get(nombre)
        if g is None:
            g = grupos[nombre] = {'transporte': nombre, 'destinatarios': [],
                                  'cantidad_remitos': 0, 'total_bultos': 0}
        g['destinatarios'].append(d)
        g['cantidad_remitos'] += len(d['remitos'])
        g['total_bultos'] += d['total_bultos']
    return list(grupos.values())  # ya vienen ordenados por agrupar_por_destinatario
