from dataclasses import dataclass


@dataclass
class ConfigSQLServer:
    server: str = ''
    database: str = ''
    username: str = ''
    password: str = ''
    trusted: bool = True

    @property
    def connection_string(self) -> str:
        if self.trusted:
            return (
                f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                f'SERVER={self.server};'
                f'DATABASE={self.database};'
                f'Trusted_Connection=yes;'
            )
        return (
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            f'UID={self.username};'
            f'PWD={self.password};'
        )


@dataclass
class ConfigMySQL:
    host: str = 'localhost'
    port: int = 3306
    database: str = ''
    username: str = ''
    password: str = ''


@dataclass
class ConfigImpresoras:
    impresora_remitos: str = ''
    tamanio_papel_remitos: str = 'A4'
    orientacion_remitos: str = 'Vertical'
    copias_remitos: int = 1
    bandeja_remitos: str = 'Automática'
    margen_superior_remitos: float = 10.0
    margen_inferior_remitos: float = 10.0
    margen_izquierdo_remitos: float = 10.0
    margen_derecho_remitos: float = 10.0

    impresora_etiquetas: str = ''
    tipo_etiqueta: str = ''
    ancho_etiqueta: float = 100.0
    alto_etiqueta: float = 50.0
    columnas_etiqueta: int = 2
    filas_etiqueta: int = 5
    tamanio_papel_etiquetas: str = 'A4'
    bandeja_etiquetas: str = 'Automática'

    scanner: str = ''

    TAMANIOS_PAPEL = ['A4', 'A5', 'A3', 'Letter', 'Legal', 'Oficio', 'Custom']
    ORIENTACIONES = ['Vertical', 'Horizontal']
    BANDEJAS = ['Automática', 'Bandeja 1', 'Bandeja 2', 'Bandeja 3']
    TIPOS_ETIQUETA = [
        '2 x 1 (99.1 x 42.3 mm)',
        '3 x 1 (66.0 x 42.3 mm)',
        '4 x 2 (49.0 x 25.4 mm)',
        '4 x 1 (49.0 x 42.3 mm)',
        '2 x 2 (99.1 x 25.4 mm)',
        'Personalizado',
    ]


@dataclass
class ConfigImpresion:
    remitente_nombre: str = ''
    remitente_direccion: str = ''
    remitente_ciudad: str = ''
    remitente_cuit: str = ''
    remitente_telefono: str = ''
    prox_numero_remito: int = 1
    prefijo_remito: str = 'R-'
    sucursales_excluidas: str = ''
    importe_unitario_valor_declarado: float = 0.0
