import pyodbc
from database.conexiones import ConfigSQLServer, resolve_driver, get_available_drivers, DRIVER_PRIORITY, get_driver_download_url


class SQLServerConnection:
    def __init__(self, config: ConfigSQLServer):
        self.config = config
        self._conn: pyodbc.Connection | None = None
        self._driver: str = ''

    def connect(self):
        if self._conn is not None:
            try:
                cur = self._conn.cursor()
                cur.execute('SELECT 1')
                cur.close()
                return self._conn
            except Exception:
                self._conn = None

        drivers_to_try = self._get_drivers_to_try()
        last_error = ''

        for d in drivers_to_try:
            try:
                conn_str = self.config.build_connection_str(driver=d)
                self._conn = pyodbc.connect(conn_str, timeout=5)
                self._driver = d
                return self._conn
            except pyodbc.Error as e:
                last_error = str(e)
                if 'IM002' not in str(e) and 'driver' not in str(e).lower():
                    self._conn = None
                    raise

        self._conn = None
        msg = self._build_driver_error(drivers_to_try, last_error)
        raise RuntimeError(msg)

    def _get_drivers_to_try(self) -> list[str]:
        available = get_available_drivers()
        # build a list of priority drivers that are installed
        ordered = [d for d in DRIVER_PRIORITY if d in available]
        # add any other installed driver not in priority list (variantes
        # regionales/legacy que el usuario no puede actualizar)
        for d in available:
            if d not in ordered:
                ordered.append(d)
        # el driver configurado explícitamente se intenta primero, pero si
        # falla igual se siguen probando el resto de los instalados
        if self.config.driver and self.config.driver in ordered:
            ordered.remove(self.config.driver)
            ordered.insert(0, self.config.driver)
        return ordered

    def _build_driver_error(self, tried: list[str], last_error: str) -> str:
        available = get_available_drivers()
        if not available:
            return (
                'No hay drivers ODBC para SQL Server instalados.\n'
                f'Descargue e instale desde:\n{get_driver_download_url()}'
            )
        if last_error and 'IM002' not in last_error:
            return last_error
        return (
            'No se pudo conectar con ningún driver ODBC disponible.\n'
            f'Drivers probados: {", ".join(tried)}\n\n'
            f'Descargue ODBC Driver 17 desde:\n{get_driver_download_url()}'
        )

    def disconnect(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def test_connection(self) -> tuple[bool, str]:
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            return True, ''
        except Exception as e:
            self._conn = None
            return False, str(e)

    def buscar_recepciones(
        self, filtro: str = '', dias: int = 365, destino: str = '', material: str = ''
    ) -> list[dict]:
        conn = self.connect()
        cursor = conn.cursor()
        sql = '''
            SELECT
                T1.[IDRecepcion],
                T1.IDClaseRecepcion,
                T2.Descripcion AS ClaseDescripcion,
                T1.[IDProveedor],
                T3.Descripcion AS RazonSocial,
                T1.[FechaPrevista],
                ('CCU' + T1.CartaDePorte) AS SucursalDestino,
                T4.Descripcion AS NombreDestino,
                T1.[StRecepcion],
                T1.[StCierre],
                T4.Domicilio AS DomicilioCliente,
                T4.CodigoPostal AS CodigoPostalCliente,
                T4.Ciudad AS CiudadCliente,
                T4.Distrito AS DistritoCliente,
                T5.Descripcion AS TransporteDescripcion,
                T5.DatosPrivados1 AS TransporteDatosPrivados
            FROM ctRecepcionesPrevistas T1 WITH(NOLOCK)
                LEFT JOIN clasesrecepcion T2 WITH(NOLOCK)
                    ON T1.IDClaseRecepcion = T2.IdClaseRecepcion
                LEFT JOIN proveedores T3 WITH(NOLOCK)
                    ON T1.IDProveedor = T3.NumProveedor
                LEFT JOIN clientes T4 WITH(NOLOCK)
                    ON T4.NumCliente = 'CCU' + T1.CartaDePorte
                LEFT JOIN ctTransporte T5 WITH(NOLOCK)
                    ON T5.IdTransporte = T4.TransporteDefault
            WHERE
                T1.IDClaseRecepcion IN ('RCOC', 'RCFI')
                AND T1.UltimaActualizacionFecha > DATEADD(DAY, -?, GETDATE())
                AND ISNULL(T1.StCierre, '') != 'C'
                AND (T1.IDRecepcion LIKE ?
                     OR T3.NumProveedor LIKE ?
                     OR T3.Descripcion LIKE ?)
                AND ISNULL(T4.Descripcion, '') LIKE ?
                AND (? = '' OR EXISTS (
                    SELECT 1
                    FROM ctRecepcionesPrevistasPosiciones P WITH(NOLOCK)
                    WHERE P.IDRecepcion = T1.IDRecepcion
                      AND P.IDMaterial LIKE ?
                ))
            ORDER BY T1.FechaPrevista DESC
        '''
        pattern = f'%{filtro}%'
        dest_pattern = f'%{destino}%'
        material_pattern = f'%{material}%'
        cursor.execute(
            sql,
            (dias, pattern, pattern, pattern, dest_pattern, material, material_pattern),
        )
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        cursor.close()
        return [dict(zip(columns, row)) for row in rows]

    def buscar_recepciones_por_ids(self, ids: list[str]) -> list[dict]:
        if not ids:
            return []
        conn = self.connect()
        cursor = conn.cursor()
        like_conditions = ' OR '.join('T1.[IDRecepcion] LIKE ?' for _ in ids)
        like_params = [f'%{i}%' for i in ids]
        sql = f'''
            SELECT
                T1.[IDRecepcion],
                T1.IDClaseRecepcion,
                T2.Descripcion AS ClaseDescripcion,
                T1.[IDProveedor],
                T3.Descripcion AS RazonSocial,
                T1.[FechaPrevista],
                ('CCU' + T1.CartaDePorte) AS SucursalDestino,
                T4.Descripcion AS NombreDestino,
                T1.[StRecepcion],
                T1.[StCierre],
                T4.Domicilio AS DomicilioCliente,
                T4.CodigoPostal AS CodigoPostalCliente,
                T4.Ciudad AS CiudadCliente,
                T4.Distrito AS DistritoCliente,
                T5.Descripcion AS TransporteDescripcion,
                T5.DatosPrivados1 AS TransporteDatosPrivados
            FROM ctRecepcionesPrevistas T1 WITH(NOLOCK)
                LEFT JOIN clasesrecepcion T2 WITH(NOLOCK)
                    ON T1.IDClaseRecepcion = T2.IdClaseRecepcion
                LEFT JOIN proveedores T3 WITH(NOLOCK)
                    ON T1.IDProveedor = T3.NumProveedor
                LEFT JOIN clientes T4 WITH(NOLOCK)
                    ON T4.NumCliente = 'CCU' + T1.CartaDePorte
                LEFT JOIN ctTransporte T5 WITH(NOLOCK)
                    ON T5.IdTransporte = T4.TransporteDefault
            WHERE ({like_conditions})
                AND T1.IDClaseRecepcion IN ('RCOC', 'RCFI')
                AND ISNULL(T1.StCierre, '') != 'C'
        '''
        cursor.execute(sql, like_params)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        cursor.close()
        return [dict(zip(columns, row)) for row in rows]

    def buscar_recepciones_por_proveedor_destino(
        self, id_proveedor: str, nombre_destino: str
    ) -> list[dict]:
        conn = self.connect()
        cursor = conn.cursor()
        sql = '''
            SELECT
                T1.[IDRecepcion],
                T1.IDClaseRecepcion,
                T2.Descripcion AS ClaseDescripcion,
                T1.[IDProveedor],
                T3.Descripcion AS RazonSocial,
                T1.[FechaPrevista],
                ('CCU' + T1.CartaDePorte) AS SucursalDestino,
                T4.Descripcion AS NombreDestino,
                T1.[StRecepcion],
                T1.[StCierre],
                T4.Domicilio AS DomicilioCliente,
                T4.CodigoPostal AS CodigoPostalCliente,
                T4.Ciudad AS CiudadCliente,
                T4.Distrito AS DistritoCliente,
                T5.Descripcion AS TransporteDescripcion,
                T5.DatosPrivados1 AS TransporteDatosPrivados
            FROM ctRecepcionesPrevistas T1 WITH(NOLOCK)
                LEFT JOIN clasesrecepcion T2 WITH(NOLOCK)
                    ON T1.IDClaseRecepcion = T2.IdClaseRecepcion
                LEFT JOIN proveedores T3 WITH(NOLOCK)
                    ON T1.IDProveedor = T3.NumProveedor
                LEFT JOIN clientes T4 WITH(NOLOCK)
                    ON T4.NumCliente = 'CCU' + T1.CartaDePorte
                LEFT JOIN ctTransporte T5 WITH(NOLOCK)
                    ON T5.IdTransporte = T4.TransporteDefault
            WHERE
                T1.IDClaseRecepcion IN ('RCOC', 'RCFI')
                AND ISNULL(T1.StCierre, '') != 'C'
                AND T1.IDProveedor = ?
                AND T4.Descripcion = ?
            ORDER BY T1.FechaPrevista DESC
        '''
        cursor.execute(sql, (id_proveedor, nombre_destino))
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        cursor.close()
        return [dict(zip(columns, row)) for row in rows]

    def buscar_materiales_por_recepcion(self, id_recepcion: str) -> list[dict]:
        conn = self.connect()
        cursor = conn.cursor()
        sql = '''
            SELECT
                T1.[IDRecepcion],
                T1.[IDPosicion],
                T1.IDMaterial,
                T2.DatosPrivados1,
                T2.Descripcion,
                T1.[CantidadPrevista],
                T1.[CantidadRecepcionada]
            FROM ctRecepcionesPrevistasPosiciones T1 WITH(NOLOCK)
            INNER JOIN Materiales T2 WITH(NOLOCK)
                ON T1.IDMaterial = T2.NumMaterial
            WHERE T1.IDRecepcion = ?
        '''
        cursor.execute(sql, (id_recepcion,))
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        cursor.close()
        return [dict(zip(columns, row)) for row in rows]

    def validar_recepcion(self, id_recepcion: str, id_proveedor: str) -> dict | None:
        conn = self.connect()
        cursor = conn.cursor()
        sql = '''
            SELECT
                T1.[IDRecepcion],
                T1.IDClaseRecepcion,
                T2.Descripcion AS ClaseDescripcion,
                T1.[IDProveedor],
                T3.Descripcion AS RazonSocial,
                T1.[FechaPrevista],
                ('CCU' + T1.CartaDePorte) AS SucursalDestino,
                T4.Descripcion AS NombreDestino,
                T1.[StRecepcion],
                T1.[StCierre],
                T4.Domicilio AS DomicilioCliente,
                T4.CodigoPostal AS CodigoPostalCliente,
                T4.Ciudad AS CiudadCliente,
                T4.Distrito AS DistritoCliente,
                T5.Descripcion AS TransporteDescripcion,
                T5.DatosPrivados1 AS TransporteDatosPrivados
            FROM ctRecepcionesPrevistas T1 WITH(NOLOCK)
                INNER JOIN clasesrecepcion T2 WITH(NOLOCK)
                    ON T1.IDClaseRecepcion = T2.IdClaseRecepcion
                INNER JOIN proveedores T3 WITH(NOLOCK)
                    ON T1.IDProveedor = T3.NumProveedor
                INNER JOIN clientes T4 WITH(NOLOCK)
                    ON T4.NumCliente = 'CCU' + T1.CartaDePorte
                LEFT JOIN ctTransporte T5 WITH(NOLOCK)
                    ON T5.IdTransporte = T4.TransporteDefault
            WHERE T1.IDRecepcion = ?
                AND T1.IDProveedor = ?
                AND T1.IDClaseRecepcion IN ('RCOC', 'RCFI')
        '''
        cursor.execute(sql, (id_recepcion, id_proveedor))
        row = cursor.fetchone()
        if row:
            columns = [col[0] for col in cursor.description]
            result = dict(zip(columns, row))
            cursor.close()
            return result
        cursor.close()
        return None

    def obtener_datos_cliente(self, num_cliente: str) -> dict | None:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT Descripcion, Domicilio, CodigoPostal, Ciudad, Distrito '
            'FROM clientes WITH(NOLOCK) WHERE NumCliente = ?',
            (num_cliente,)
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None
        return {
            'nombre': row[0] or '',
            'domicilio': row[1] or '',
            'codigo_postal': row[2] or '',
            'ciudad': row[3] or '',
            'distrito': row[4] or '',
        }

    def buscar_material_por_codigo(self, codigo: str) -> dict | None:
        conn = self.connect()
        cursor = conn.cursor()
        sql = '''
            SELECT TOP 1
                M.NumMaterial,
                M.Descripcion,
                E.CodigoUnidad,
                E.EAN
            FROM Materiales M WITH(NOLOCK)
            LEFT JOIN MaterialesEANPresentaciones E WITH(NOLOCK)
                ON E.NumMaterial = M.NumMaterial
                AND E.CodigoUnidad = 'UN'
                AND (E.Numero = 1 OR E.Principal = 1)
            WHERE M.NumMaterial = ?
        '''
        cursor.execute(sql, (codigo,))
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None
        return dict(zip(['NumMaterial', 'Descripcion', 'CodigoUnidad', 'EAN'], row))

    def obtener_datos_proveedor(self, num_proveedor: str) -> dict | None:
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT Descripcion, Domicilio, CodigoPostal, Ciudad, Distrito '
            'FROM proveedores WITH(NOLOCK) WHERE NumProveedor = ?',
            (num_proveedor,)
        )
        row = cursor.fetchone()
        cursor.close()
        if not row:
            return None
        return {
            'nombre': row[0] or '',
            'domicilio': row[1] or '',
            'codigo_postal': row[2] or '',
            'ciudad': row[3] or '',
            'distrito': row[4] or '',
        }
