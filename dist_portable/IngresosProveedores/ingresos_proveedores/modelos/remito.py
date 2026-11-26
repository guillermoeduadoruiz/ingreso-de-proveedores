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

    @property
    def texto_bultos(self) -> str:
        """Texto para grillas: un remito con 0 bultos viaja dentro del bulto de otro remito."""
        if self.cantidad_bultos == 0:
            return '0 (en otro bulto)'
        return str(self.cantidad_bultos)


def destinos_sin_bultos(remitos: list[Remito]) -> list[str]:
    """Devuelve los nombres de destino cuyos remitos suman 0 bultos.

    Varios remitos pueden viajar en un mismo bulto físico (se cargan con 0 bultos),
    pero ese bulto siempre va a un único destino, así que cada destino necesita
    al menos un remito con bultos > 0.
    """
    totales: dict[str, int] = {}
    nombres: dict[str, str] = {}
    for remito in remitos:
        for suc in {rp.sucursal_destino for rp in remito.recepciones}:
            totales[suc] = totales.get(suc, 0) + remito.cantidad_bultos
        for rp in remito.recepciones:
            nombres.setdefault(rp.sucursal_destino, rp.nombre_destino or rp.sucursal_destino)
    return [nombres[suc] for suc, total in totales.items() if total == 0]
