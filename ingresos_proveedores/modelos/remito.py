from dataclasses import dataclass, field
from datetime import date
from modelos.recepcion import RecepcionPrevista


@dataclass
class Remito:
    num_remito: str
    fecha_remito: date
    cantidad_bultos: int
    cantidad_unidades: int = 0
    valor_declarado_unitario: float = 0.0
    recepciones: list[RecepcionPrevista] = field(default_factory=list)
    id_remito: int | None = None

    @property
    def valor_declarado_total(self) -> float:
        if self.cantidad_unidades > 0 and self.valor_declarado_unitario > 0:
            return self.cantidad_unidades * self.valor_declarado_unitario
        return 0.0
