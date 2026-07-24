from dataclasses import dataclass, field
from datetime import date, datetime
from modelos.remito import Remito
from modelos.proveedor import Proveedor


@dataclass
class Ingreso:
    id_ingreso: str
    fecha_ingreso: date
    proveedor: Proveedor
    remitos: list[Remito] = field(default_factory=list)
    creado: datetime | None = None
