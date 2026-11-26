from datetime import date
from database.mysql import MySQLConnection
from modelos.proveedor import Proveedor
from modelos.remito import Remito
from modelos.recepcion import RecepcionPrevista
from modelos.ingreso import Ingreso
from servicios.generador_id import generar_id_ingreso


class IngresoService:
    def __init__(self, mysql: MySQLConnection):
        self._mysql = mysql

    def registrar(self, proveedor: Proveedor, remitos: list[Remito], fecha_ingreso: date = None) -> Ingreso:
        if not remitos:
            raise ValueError('No se puede registrar un ingreso sin remitos asociados.')

        for remito in remitos:
            if self.remito_ya_registrado(remito.num_remito, proveedor.num_proveedor):
                raise ValueError(
                    f'El remito N° {remito.num_remito} ya fue registrado '
                    f'para el proveedor {proveedor.num_proveedor}.'
                )

        id_ingreso = generar_id_ingreso()
        fecha_ingreso = fecha_ingreso or date.today()

        self._mysql.begin()
        try:
            self._mysql.save_ingreso(id_ingreso, fecha_ingreso, proveedor.num_proveedor, proveedor.descripcion)

            for remito in remitos:
                id_remito = self._mysql.save_remito(
                    id_ingreso, remito.num_remito,
                    remito.fecha_remito, remito.cantidad_bultos,
                    proveedor.num_proveedor, remito.cantidad_unidades,
                    remito.valor_declarado_unitario
                )
                recepciones_unicas = {
                    rp.id_recepcion: rp for rp in remito.recepciones
                }.values()
                for recepcion in recepciones_unicas:
                    self._mysql.save_remito_recepcion(
                        id_remito, recepcion.id_recepcion,
                        recepcion.sucursal_destino,
                        recepcion.nombre_destino,
                        recepcion.domicilio_cliente,
                        recepcion.codigo_postal_cliente,
                        recepcion.ciudad_cliente,
                        recepcion.distrito_cliente,
                        recepcion.transporte_descripcion,
                        recepcion.transporte_datos_privados,
                    )

            self._mysql.commit()
        except Exception:
            self._mysql.rollback()
            raise

        return Ingreso(
            id_ingreso=id_ingreso,
            fecha_ingreso=fecha_ingreso,
            proveedor=proveedor,
            remitos=remitos,
        )

    def remito_ya_registrado(self, num_remito: str, num_proveedor: str) -> bool:
        return self._mysql.remito_exists(num_remito, num_proveedor)

    def obtener_ingresos_recientes(self, limite: int = 50) -> list[dict]:
        return self._mysql.get_ingresos_recientes(limite)

    def obtener_remitos_por_ingreso(self, id_ingreso: str) -> list[dict]:
        return self._mysql.get_remitos_por_ingreso(id_ingreso)

    def obtener_recepciones_por_remito(self, id_remito: int) -> list[dict]:
        return self._mysql.get_recepciones_por_remito(id_remito)

    def eliminar_ingreso(self, id_ingreso: str):
        self._mysql.delete_ingreso(id_ingreso)

    def guardar_remito_generado(self, id_ingreso: str, num_remito: str, destino: str = ''):
        self._mysql.save_remito_generado(id_ingreso, num_remito, destino)

    def obtener_remito_generado(self, id_ingreso: str, destino: str = '') -> str | None:
        return self._mysql.get_remito_generado(id_ingreso, destino)

    def obtener_remitos_generados(self, id_ingreso: str) -> list[dict]:
        return self._mysql.get_remitos_generados(id_ingreso)

    def obtener_remitos_generados_por_ingresos(self, ids_ingreso: list[str]) -> dict[str, list[dict]]:
        return self._mysql.get_remitos_generados_por_ingresos(ids_ingreso)

    def obtener_consulta_destinatarios(self, fecha_desde=None, fecha_hasta=None) -> list[dict]:
        return self._mysql.get_consulta_destinatarios(fecha_desde, fecha_hasta)

    def actualizar_estado_remito_generado(self, id_ingreso: str, destino: str, estado: int) -> int:
        return self._mysql.update_estado_remito_generado(id_ingreso, destino, estado)

    def obtener_ingreso_completo(self, id_ingreso: str) -> Ingreso | None:
        data = self._mysql.get_ingreso_completo(id_ingreso)
        if not data:
            return None
        row_ing = data['ingreso']
        proveedor = Proveedor(
            num_proveedor=row_ing['num_proveedor'],
            descripcion=row_ing['razon_social'],
            domicilio='', codigo_postal='', ciudad='', distrito='',
        )
        remitos = []
        for row_rem in data['remitos']:
            recepciones = []
            for row_rec in row_rem.get('recepciones', []):
                recepciones.append(RecepcionPrevista(
                    id_recepcion=row_rec['id_recepcion_prevista'],
                    id_clase_recepcion='',
                    descripcion_clase='',
                    id_proveedor=row_rem.get('num_proveedor', ''),
                    razon_social=row_ing['razon_social'],
                    fecha_prevista=row_rem['fecha_remito'],
                    sucursal_destino=row_rec.get('sucursal_destino', ''),
                    nombre_destino=row_rec.get('nombre_destino', ''),
                    st_recepcion='',
                    st_cierre='',
                    domicilio_cliente=row_rec.get('domicilio_cliente', ''),
                    codigo_postal_cliente=row_rec.get('codigo_postal_cliente', ''),
                    ciudad_cliente=row_rec.get('ciudad_cliente', ''),
                    distrito_cliente=row_rec.get('distrito_cliente', ''),
                    transporte_descripcion=row_rec.get('transporte_descripcion', ''),
                    transporte_datos_privados=row_rec.get('transporte_datos_privados', ''),
                ))
            remitos.append(Remito(
                num_remito=row_rem['num_remito'],
                fecha_remito=row_rem['fecha_remito'],
                cantidad_bultos=row_rem['cantidad_bultos'],
                cantidad_unidades=row_rem.get('cantidad_unidades', 0),
                valor_declarado_unitario=row_rem.get('valor_declarado_unitario', 0.0),
                recepciones=recepciones,
                id_remito=row_rem['id_remito'],
            ))
        return Ingreso(
            id_ingreso=row_ing['id_ingreso'],
            fecha_ingreso=row_ing['fecha_ingreso'],
            proveedor=proveedor,
            remitos=remitos,
            creado=row_ing.get('creado'),
        )
