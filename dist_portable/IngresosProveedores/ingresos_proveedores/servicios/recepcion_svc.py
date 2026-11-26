from datetime import datetime
from database.sqlserver import SQLServerConnection
from modelos.recepcion import RecepcionPrevista


class RecepcionService:
    def __init__(self, sqlserver: SQLServerConnection):
        self._sqlserver = sqlserver

    def buscar(
        self, filtro: str = '', dias: int = 365, destino: str = '', material: str = ''
    ) -> list[RecepcionPrevista]:
        rows = self._sqlserver.buscar_recepciones(filtro, dias, destino, material)
        return [self._row_to_recepcion(r) for r in rows]

    def buscar_por_ids(self, ids: list[str]) -> list[RecepcionPrevista]:
        rows = self._sqlserver.buscar_recepciones_por_ids(ids)
        return [self._row_to_recepcion(r) for r in rows]

    def buscar_por_proveedor_destino(
        self, id_proveedor: str, nombre_destino: str
    ) -> list[RecepcionPrevista]:
        try:
            rows = self._sqlserver.buscar_recepciones_por_proveedor_destino(
                id_proveedor, nombre_destino
            )
            return [self._row_to_recepcion(r) for r in rows]
        except Exception:
            return []

    def validar(self, id_recepcion: str, id_proveedor: str) -> RecepcionPrevista | None:
        row = self._sqlserver.validar_recepcion(id_recepcion, id_proveedor)
        if row:
            return self._row_to_recepcion(row)
        return None

    def buscar_materiales(self, id_recepcion: str) -> list[dict]:
        try:
            return self._sqlserver.buscar_materiales_por_recepcion(id_recepcion)
        except Exception:
            return []

    def _row_to_recepcion(self, row: dict) -> RecepcionPrevista:
        fecha = row.get('FechaPrevista')
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        return RecepcionPrevista(
            id_recepcion=str(row['IDRecepcion']),
            id_clase_recepcion=row.get('IDClaseRecepcion') or '',
            descripcion_clase=row.get('ClaseDescripcion') or '',
            id_proveedor=str(row.get('IDProveedor') or ''),
            razon_social=row.get('RazonSocial') or '',
            fecha_prevista=fecha,
            sucursal_destino=row.get('SucursalDestino') or '',
            nombre_destino=row.get('NombreDestino') or '',
            st_recepcion=row.get('StRecepcion') or '',
            st_cierre=row.get('StCierre') or '',
            domicilio_cliente=row.get('DomicilioCliente') or '',
            codigo_postal_cliente=row.get('CodigoPostalCliente') or '',
            ciudad_cliente=row.get('CiudadCliente') or '',
            distrito_cliente=row.get('DistritoCliente') or '',
            transporte_descripcion=row.get('TransporteDescripcion') or '',
            transporte_datos_privados=row.get('TransporteDatosPrivados') or '',
        )
