from database.mysql import MySQLConnection
from database.sqlserver import SQLServerConnection
from modelos.hoja_ruta import HojaRuta, HR_EN_PREPARACION


class HojaRutaService:
    """Armado y despacho de hojas de ruta a partir de los remitos emitidos.

    Un remito emitido (fila de ingresoscd_remitos_generados) queda pendiente de
    despacho mientras esté en estado Emitido / En Muelle y no pertenezca a una
    hoja de ruta activa. Al confirmar el despacho de la hoja, sus remitos pasan
    a estado Despachado.
    """

    def __init__(self, mysql: MySQLConnection, sqlserver: SQLServerConnection | None = None):
        self._mysql = mysql
        self._sqlserver = sqlserver

    def _completar_transporte(self, remitos: list[dict]) -> list[dict]:
        """Toma el transporte actual del cliente destino desde SQL Server
        (clientes.TransporteDefault → ctTransporte.Descripcion). Si SQL Server no
        responde o el cliente no tiene transporte, queda el valor grabado en MySQL
        al momento del ingreso."""
        if not self._sqlserver or not remitos:
            return remitos
        try:
            transportes = self._sqlserver.get_transportes_clientes(
                [str(r.get('sucursal_destino') or '').strip() for r in remitos]
            )
        except Exception:
            return remitos
        for r in remitos:
            t = transportes.get(str(r.get('sucursal_destino') or '').strip())
            if t:
                r['transporte_descripcion'] = t
        return remitos

    def obtener_pendientes(self, id_hoja: int | None = None) -> list[dict]:
        return self._completar_transporte(self._mysql.get_remitos_pendientes_despacho(id_hoja))

    def listar(self, fecha_desde=None, fecha_hasta=None, estado: int | None = None) -> list[HojaRuta]:
        filas = self._mysql.get_hojas_ruta(fecha_desde, fecha_hasta, estado)
        remitos = self._mysql.get_remitos_de_hojas([f['id_hoja'] for f in filas])
        self._completar_transporte([r for lista in remitos.values() for r in lista])
        return [HojaRuta.desde_fila(f, remitos.get(f['id_hoja'], [])) for f in filas]

    def obtener(self, id_hoja: int) -> HojaRuta | None:
        fila = self._mysql.get_hoja_ruta(id_hoja)
        if not fila:
            return None
        remitos = self._completar_transporte(
            self._mysql.get_remitos_de_hojas([id_hoja]).get(id_hoja, []))
        return HojaRuta.desde_fila(fila, remitos)

    def guardar(self, hoja: HojaRuta, ids_remito_generado: list[int]) -> HojaRuta:
        """Crea o actualiza una hoja en preparación con los remitos indicados."""
        ids = sorted(set(ids_remito_generado))
        if not ids:
            raise ValueError('Seleccione al menos un remito para la hoja de ruta.')
        if hoja.id_hoja and hoja.estado != HR_EN_PREPARACION:
            raise ValueError('Solo se puede modificar una hoja de ruta en preparación.')

        self._mysql.begin()
        try:
            conflictos = self._mysql.get_remitos_en_otra_hoja(ids, hoja.id_hoja)
            if conflictos:
                detalle = '\n'.join(
                    f'  • {c["num_remito"]} ({c["destino"]}) → hoja {c["id_hoja"]:06d}'
                    for c in conflictos
                )
                raise ValueError(f'Estos remitos ya están en otra hoja de ruta:\n{detalle}')
            datos = (hoja.fecha_despacho, hoja.transportista.strip(), hoja.chofer.strip(),
                     hoja.patente.strip().upper(), hoja.observaciones.strip())
            if hoja.id_hoja:
                if self._mysql.update_hoja_ruta(hoja.id_hoja, *datos) == 0 and \
                        not self._sigue_en_preparacion(hoja.id_hoja):
                    raise ValueError('La hoja de ruta ya no está en preparación.')
                id_hoja = hoja.id_hoja
            else:
                id_hoja = self._mysql.insert_hoja_ruta(*datos)
            self._mysql.reemplazar_remitos_hoja(id_hoja, ids)
            self._mysql.commit()
        except Exception:
            self._mysql.rollback()
            raise
        return self.obtener(id_hoja)

    def _sigue_en_preparacion(self, id_hoja: int) -> bool:
        fila = self._mysql.get_hoja_ruta(id_hoja)
        return bool(fila) and int(fila['estado']) == HR_EN_PREPARACION

    def confirmar_despacho(self, id_hoja: int):
        self._mysql.begin()
        try:
            if not self._mysql.confirmar_despacho_hoja(id_hoja):
                raise ValueError('La hoja de ruta no está en preparación.')
            self._mysql.commit()
        except Exception:
            self._mysql.rollback()
            raise

    def anular(self, id_hoja: int):
        self._mysql.begin()
        try:
            if not self._mysql.anular_hoja_ruta(id_hoja):
                raise ValueError('La hoja de ruta ya estaba anulada.')
            self._mysql.commit()
        except Exception:
            self._mysql.rollback()
            raise
