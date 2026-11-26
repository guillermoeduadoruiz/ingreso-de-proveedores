from dataclasses import dataclass, field
from datetime import date


@dataclass
class RecepcionPrevista:
    id_recepcion: str
    id_clase_recepcion: str
    descripcion_clase: str
    id_proveedor: str
    razon_social: str
    fecha_prevista: date
    sucursal_destino: str
    nombre_destino: str
    st_recepcion: str
    st_cierre: str
    domicilio_cliente: str = ''
    codigo_postal_cliente: str = ''
    ciudad_cliente: str = ''
    distrito_cliente: str = ''
    transporte_descripcion: str = ''
    transporte_datos_privados: str = ''
