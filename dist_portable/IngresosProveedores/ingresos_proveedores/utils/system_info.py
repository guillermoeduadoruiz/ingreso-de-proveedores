STATUS_TEXTS = {
    0x00000001: 'En pausa',
    0x00000002: 'Error',
    0x00000004: 'Pendiente de eliminación',
    0x00000008: 'Atasco de papel',
    0x00000010: 'Sin papel',
    0x00000020: 'Alimentación manual',
    0x00000040: 'Problema de papel',
    0x00000080: 'Desconectada / Fuera de línea',
    0x00000100: 'Transferencia activa',
    0x00000200: 'Ocupada',
    0x00000400: 'Imprimiendo',
    0x00000800: 'Bandeja de salida llena',
    0x00001000: 'No disponible',
    0x00002000: 'En espera',
    0x00004000: 'Procesando',
    0x00008000: 'Inicializando',
    0x00010000: 'Calentando',
    0x00020000: 'Poco tóner',
    0x00040000: 'Sin tóner',
    0x00080000: 'Página omitida',
    0x00100000: 'Requiere intervención',
    0x00200000: 'Sin memoria',
    0x00400000: 'Puerta abierta',
    0x00800000: 'Servidor desconocido',
    0x01000000: 'Ahorro de energía',
}


def verificar_impresora(nombre: str) -> tuple[bool, str]:
    if not nombre.strip():
        return False, 'No se especificó ninguna impresora.'
    try:
        import win32print
        handle = win32print.OpenPrinter(nombre.strip())
        try:
            info = win32print.GetPrinter(handle, 2)
            status = info.get('Status', 0)
            if status == 0:
                return True, 'Conectada y disponible.'
            mensajes = []
            for bit, texto in STATUS_TEXTS.items():
                if status & bit:
                    mensajes.append(texto)
            if not mensajes:
                mensajes.append(f'Estado desconocido ({status})')
            return False, ' | '.join(mensajes)
        finally:
            win32print.ClosePrinter(handle)
    except ImportError:
        return False, 'Módulo pywin32 no disponible.'
    except Exception as e:
        return False, str(e)[:100]


def listar_impresoras() -> list[str]:
    try:
        import win32print
        printers = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        )
        return sorted(set(p[2] for p in printers))
    except ImportError:
        return []


def listar_scanners() -> list[str]:
    try:
        import win32com.client
        wia = win32com.client.Dispatch('WIA.DeviceManager')
        devices = wia.DeviceInfos
        result = []
        for d in devices:
            props = d.Properties
            for p in props:
                if p.Name == 'Name':
                    result.append(p.Value)
                    break
        return sorted(result)
    except Exception:
        return []
