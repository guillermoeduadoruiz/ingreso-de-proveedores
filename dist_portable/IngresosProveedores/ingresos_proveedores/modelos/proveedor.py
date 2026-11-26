from dataclasses import dataclass


@dataclass
class Proveedor:
    num_proveedor: str
    descripcion: str
    domicilio: str
    codigo_postal: str
    ciudad: str
    distrito: str
