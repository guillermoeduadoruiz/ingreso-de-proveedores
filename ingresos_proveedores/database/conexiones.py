from dataclasses import dataclass, field
import pyodbc

DRIVER_PRIORITY = [
    'ODBC Driver 17 for SQL Server',
    'ODBC Driver 18 for SQL Server',
    'ODBC Driver 13 for SQL Server',
    'ODBC Driver 11 for SQL Server',
    'SQL Server Native Client 11.0',
    'SQL Server Native Client 10.0',
    'SQL Native Client',
    'SQL Server',
]


def get_available_drivers() -> list[str]:
    try:
        return list(pyodbc.drivers())
    except Exception:
        return []


def resolve_driver(preferred: str = '') -> str:
    available = get_available_drivers()
    if not available:
        return ''
    if preferred and preferred in available:
        return preferred
    for d in DRIVER_PRIORITY:
        if d in available:
            return d
    return available[0]


def build_connection_str(
    server: str,
    database: str,
    trusted: bool = True,
    username: str = '',
    password: str = '',
    driver: str = '',
) -> str:
    resolved = resolve_driver(driver)
    if not resolved:
        if driver:
            msg = f'Driver ODBC "{driver}" no encontrado. '
        else:
            msg = 'No se encontró ningún driver ODBC para SQL Server. '
        msg += 'Instale "ODBC Driver 17 for SQL Server" desde https://go.microsoft.com/fwlink/?linkid=2222570'
        raise RuntimeError(msg)
    if trusted:
        return (
            f'DRIVER={{{resolved}}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'Trusted_Connection=yes;'
        )
    return (
        f'DRIVER={{{resolved}}};'
        f'SERVER={server};'
        f'DATABASE={database};'
        f'UID={username};'
        f'PWD={password};'
    )


def test_drivers(server: str, database: str, trusted: bool = True, username: str = '', password: str = '') -> tuple[bool, str, str]:
    available = get_available_drivers()
    if not available:
        return False, 'No hay drivers ODBC para SQL Server instalados en el sistema.', ''
    # Probar primero los drivers conocidos por nombre y, si ninguno funciona,
    # cualquier otro driver instalado (p. ej. una variante regional/legacy
    # que no figure en DRIVER_PRIORITY pero que el sistema sí tenga).
    ordered = [d for d in DRIVER_PRIORITY if d in available]
    ordered += [d for d in available if d not in ordered]
    tried = []
    for d in ordered:
        try:
            if trusted:
                cs = f'DRIVER={{{d}}};SERVER={server};DATABASE={database};Trusted_Connection=yes;'
            else:
                cs = f'DRIVER={{{d}}};SERVER={server};DATABASE={database};UID={username};PWD={password};'
            conn = pyodbc.connect(cs, timeout=5)
            conn.close()
            return True, '', d
        except Exception as e:
            tried.append(f'{d}: {str(e)[:60]}')
    return False, ' | '.join(tried), ''


def get_driver_download_url() -> str:
    return 'https://go.microsoft.com/fwlink/?linkid=2222570'


@dataclass
class ConfigSQLServer:
    server: str = ''
    database: str = ''
    username: str = ''
    password: str = ''
    trusted: bool = True
    driver: str = ''

    @property
    def connection_string(self) -> str:
        if self.trusted:
            return (
                f'DRIVER={{{resolve_driver(self.driver)}}};'
                f'SERVER={self.server};'
                f'DATABASE={self.database};'
                f'Trusted_Connection=yes;'
            )
        return (
            f'DRIVER={{{resolve_driver(self.driver)}}};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            f'UID={self.username};'
            f'PWD={self.password};'
        )

    def build_connection_str(self, driver: str | None = None) -> str:
        return build_connection_str(
            server=self.server,
            database=self.database,
            trusted=self.trusted,
            username=self.username,
            password=self.password,
            driver=driver or self.driver,
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
    margen_superior_etiquetas: float = 0.0
    margen_inferior_etiquetas: float = 0.0
    margen_izquierdo_etiquetas: float = 0.0
    margen_derecho_etiquetas: float = 0.0
    separacion_etiquetas: float = 0.0

    impresora_etiquetas_mateti: str = ''
    ancho_etiqueta_mateti: float = 100.0
    alto_etiqueta_mateti: float = 150.0
    columnas_etiqueta_mateti: int = 1
    separacion_etiqueta_mateti: float = 0.0
    margen_superior_etiquetas_mateti: float = 2.0
    margen_inferior_etiquetas_mateti: float = 2.0
    margen_izquierdo_etiquetas_mateti: float = 2.0
    margen_derecho_etiquetas_mateti: float = 2.0

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
    punto_venta: str = ''
    prox_numero_remito: int = 1
    sucursales_excluidas: str = ''
    importe_unitario_valor_declarado: float = 0.0
