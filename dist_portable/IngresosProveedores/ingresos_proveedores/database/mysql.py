import pymysql
from database.conexiones import ConfigMySQL


class MySQLConnection:
    def __init__(self, config: ConfigMySQL):
        self.config = config
        self._conn: pymysql.Connection | None = None

    def connect(self) -> pymysql.Connection:
        if self._conn is not None:
            try:
                self._conn.ping(reconnect=False)
                return self._conn
            except Exception:
                self._conn = None
        self._conn = pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.username,
            password=self.config.password,
            database=self.config.database,
            charset='utf8mb4',
            autocommit=True,
            connect_timeout=5,
            ssl_disabled=True,
        )
        return self._conn

    def disconnect(self):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def begin(self):
        conn = self.connect()
        conn.autocommit(False)

    def commit(self):
        if self._conn:
            self._conn.commit()
            self._conn.autocommit(True)

    def rollback(self):
        if self._conn:
            try:
                self._conn.rollback()
            except Exception:
                pass
            self._conn.autocommit(True)

    def test_connection(self) -> tuple[bool, str]:
        try:
            conn = self.connect()
            conn.ping()
            return True, ''
        except Exception as e:
            self._conn = None
            return False, str(e)

    def initialize_schema(self):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd (
                    id_ingreso VARCHAR(50) PRIMARY KEY,
                    fecha_ingreso DATE NOT NULL,
                    num_proveedor VARCHAR(20) NOT NULL,
                    razon_social VARCHAR(200) NOT NULL,
                    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd_remitos (
                    id_remito INT AUTO_INCREMENT PRIMARY KEY,
                    id_ingreso VARCHAR(50) NOT NULL,
                    num_remito VARCHAR(50) NOT NULL,
                    fecha_remito DATE NOT NULL,
                    cantidad_bultos INT NOT NULL,
                    cantidad_unidades INT NOT NULL DEFAULT 0,
                    num_proveedor VARCHAR(20) NOT NULL,
                    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (id_ingreso) REFERENCES ingresoscd(id_ingreso),
                    UNIQUE KEY uq_remito_proveedor (num_remito, num_proveedor)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd_remito_recepciones (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_remito INT NOT NULL,
                    id_recepcion_prevista VARCHAR(50) NOT NULL,
                    sucursal_destino VARCHAR(50) NOT NULL DEFAULT '',
                    nombre_destino VARCHAR(200) NOT NULL DEFAULT '',
                    domicilio_cliente VARCHAR(200) NOT NULL DEFAULT '',
                    codigo_postal_cliente VARCHAR(20) NOT NULL DEFAULT '',
                    ciudad_cliente VARCHAR(100) NOT NULL DEFAULT '',
                    distrito_cliente VARCHAR(100) NOT NULL DEFAULT '',
                    transporte_descripcion VARCHAR(200) NOT NULL DEFAULT '',
                    transporte_datos_privados VARCHAR(200) NOT NULL DEFAULT '',
                    FOREIGN KEY (id_remito) REFERENCES ingresoscd_remitos(id_remito) ON DELETE CASCADE,
                    UNIQUE KEY uq_remito_recepcion (id_remito, id_recepcion_prevista)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd_remitos_generados (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_ingreso VARCHAR(50) NOT NULL,
                    num_remito VARCHAR(50) NOT NULL,
                    destino VARCHAR(200) NOT NULL DEFAULT '',
                    fecha_generacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    estado INT NOT NULL DEFAULT 1,
                    FOREIGN KEY (id_ingreso) REFERENCES ingresoscd(id_ingreso) ON DELETE CASCADE,
                    UNIQUE KEY uq_remito_generado (id_ingreso, destino)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            for col, default in [
                ('nombre_destino', "''"),
                ('domicilio_cliente', "''"),
                ('codigo_postal_cliente', "''"),
                ('ciudad_cliente', "''"),
                ('distrito_cliente', "''"),
                ('transporte_descripcion', "''"),
                ('transporte_datos_privados', "''"),
            ]:
                try:
                    cursor.execute(
                        f'ALTER TABLE ingresoscd_remito_recepciones '
                        f'ADD COLUMN {col} VARCHAR(200) NOT NULL DEFAULT {default}'
                    )
                except Exception:
                    pass
            try:
                cursor.execute(
                    'ALTER TABLE ingresoscd_remitos_generados '
                    'ADD COLUMN estado INT NOT NULL DEFAULT 1'
                )
            except Exception:
                pass
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd_hojas_ruta (
                    id_hoja INT AUTO_INCREMENT PRIMARY KEY,
                    fecha_despacho DATE NOT NULL,
                    transportista VARCHAR(200) NOT NULL DEFAULT '',
                    chofer VARCHAR(200) NOT NULL DEFAULT '',
                    patente VARCHAR(30) NOT NULL DEFAULT '',
                    observaciones VARCHAR(500) NOT NULL DEFAULT '',
                    estado INT NOT NULL DEFAULT 1,
                    creado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    despachado DATETIME NULL DEFAULT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ingresoscd_hoja_ruta_remitos (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    id_hoja INT NOT NULL,
                    id_remito_generado INT NOT NULL,
                    estado_previo INT NOT NULL DEFAULT 1,
                    FOREIGN KEY (id_hoja) REFERENCES ingresoscd_hojas_ruta(id_hoja) ON DELETE CASCADE,
                    FOREIGN KEY (id_remito_generado) REFERENCES ingresoscd_remitos_generados(id) ON DELETE CASCADE,
                    UNIQUE KEY uq_hoja_remito (id_hoja, id_remito_generado)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')

    def remito_exists(self, num_remito: str, num_proveedor: str) -> bool:
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM ingresoscd_remitos WHERE num_remito = %s AND num_proveedor = %s',
                (num_remito, num_proveedor)
            )
            row = cursor.fetchone()
            return row[0] > 0

    def save_ingreso(self, id_ingreso: str, fecha_ingreso, num_proveedor: str, razon_social: str):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO ingresoscd (id_ingreso, fecha_ingreso, num_proveedor, razon_social) '
                'VALUES (%s, %s, %s, %s)',
                (id_ingreso, fecha_ingreso, num_proveedor, razon_social)
            )

    def save_remito(self, id_ingreso: str, num_remito: str, fecha_remito, cantidad_bultos: int, num_proveedor: str, cantidad_unidades: int = 0, valor_declarado_unitario: float = 0.0) -> int:
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO ingresoscd_remitos (id_ingreso, num_remito, fecha_remito, cantidad_bultos, cantidad_unidades, valor_declarado_unitario, num_proveedor) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (id_ingreso, num_remito, fecha_remito, cantidad_bultos, cantidad_unidades, valor_declarado_unitario, num_proveedor)
            )
            return cursor.lastrowid

    def save_remito_recepcion(self, id_remito: int, id_recepcion_prevista: str, sucursal_destino: str = '',
                              nombre_destino: str = '', domicilio_cliente: str = '',
                              codigo_postal_cliente: str = '', ciudad_cliente: str = '',
                              distrito_cliente: str = '', transporte_descripcion: str = '',
                              transporte_datos_privados: str = ''):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO ingresoscd_remito_recepciones '
                '(id_remito, id_recepcion_prevista, sucursal_destino, nombre_destino, '
                'domicilio_cliente, codigo_postal_cliente, ciudad_cliente, distrito_cliente, '
                'transporte_descripcion, transporte_datos_privados) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (id_remito, id_recepcion_prevista, sucursal_destino, nombre_destino,
                 domicilio_cliente, codigo_postal_cliente, ciudad_cliente, distrito_cliente,
                 transporte_descripcion, transporte_datos_privados)
            )

    def save_remito_generado(self, id_ingreso: str, num_remito: str, destino: str = ''):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO ingresoscd_remitos_generados (id_ingreso, num_remito, destino, estado) '
                'VALUES (%s, %s, %s, 1) '
                'ON DUPLICATE KEY UPDATE num_remito = VALUES(num_remito)',
                (id_ingreso, num_remito, destino)
            )

    def update_estado_remito_generado(self, id_ingreso: str, destino: str, estado: int) -> int:
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE ingresoscd_remitos_generados '
                'SET estado = %s WHERE id_ingreso = %s AND destino = %s',
                (estado, id_ingreso, destino)
            )
            return cursor.rowcount

    def get_remito_generado(self, id_ingreso: str, destino: str = '') -> str | None:
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'SELECT num_remito FROM ingresoscd_remitos_generados '
                'WHERE id_ingreso = %s AND destino = %s LIMIT 1',
                (id_ingreso, destino)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def get_remitos_generados(self, id_ingreso: str) -> list[dict]:
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                'SELECT * FROM ingresoscd_remitos_generados WHERE id_ingreso = %s ORDER BY id',
                (id_ingreso,)
            )
            return cursor.fetchall()

    def get_remitos_generados_por_ingresos(self, ids_ingreso: list[str]) -> dict[str, list[dict]]:
        if not ids_ingreso:
            return {}
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            fmt = ','.join(['%s'] * len(ids_ingreso))
            cursor.execute(
                f'SELECT * FROM ingresoscd_remitos_generados '
                f'WHERE id_ingreso IN ({fmt}) ORDER BY id',
                ids_ingreso
            )
            rows = cursor.fetchall()
        result: dict[str, list[dict]] = {}
        for r in rows:
            result.setdefault(r['id_ingreso'], []).append(r)
        return result

    def get_consulta_destinatarios(self, fecha_desde=None, fecha_hasta=None) -> list[dict]:
        conn = self.connect()
        sql = '''
            SELECT g.sucursal_destino,
                   COALESCE(nd.nombre_destino, '') AS nombre_destino,
                   g.id_ingreso,
                   g.num_remito,
                   g.fecha_generacion,
                   g.estado,
                   i.fecha_ingreso,
                   i.num_proveedor,
                   i.razon_social,
                   COALESCE(b.total_bultos, 0) AS total_bultos
            FROM (
                SELECT id_ingreso, destino AS sucursal_destino, num_remito, fecha_generacion, estado
                FROM ingresoscd_remitos_generados
            ) g
            INNER JOIN ingresoscd i ON i.id_ingreso = g.id_ingreso
            LEFT JOIN (
                SELECT t.sucursal_destino, t.id_ingreso, SUM(t.cantidad_bultos) AS total_bultos
                FROM (
                    SELECT r.id_remito, r.id_ingreso, r.cantidad_bultos, rr.sucursal_destino
                    FROM ingresoscd_remitos r
                    INNER JOIN ingresoscd_remito_recepciones rr ON rr.id_remito = r.id_remito
                    GROUP BY r.id_remito, r.id_ingreso, r.cantidad_bultos, rr.sucursal_destino
                ) t
                GROUP BY t.sucursal_destino, t.id_ingreso
            ) b ON b.id_ingreso = g.id_ingreso AND b.sucursal_destino = g.sucursal_destino
            LEFT JOIN (
                SELECT sucursal_destino, MAX(nombre_destino) AS nombre_destino
                FROM ingresoscd_remito_recepciones
                WHERE nombre_destino IS NOT NULL AND nombre_destino <> ''
                GROUP BY sucursal_destino
            ) nd ON nd.sucursal_destino = g.sucursal_destino
        '''
        params = []
        where = []
        if fecha_desde is not None:
            where.append('DATE(g.fecha_generacion) >= %s')
            params.append(fecha_desde)
        if fecha_hasta is not None:
            where.append('DATE(g.fecha_generacion) <= %s')
            params.append(fecha_hasta)
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY g.sucursal_destino, g.num_remito'
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_ingresos_recientes(self, limite: int = 50) -> list[dict]:
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('''
                SELECT i.*, COUNT(r.id_remito) as cantidad_remitos
                FROM ingresoscd i
                LEFT JOIN ingresoscd_remitos r ON r.id_ingreso = i.id_ingreso
                GROUP BY i.id_ingreso, i.fecha_ingreso, i.num_proveedor,
                         i.razon_social, i.creado
                ORDER BY i.creado DESC
                LIMIT %s
            ''', (limite,))
            return cursor.fetchall()

    def get_remitos_por_ingreso(self, id_ingreso: str) -> list[dict]:
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                'SELECT * FROM ingresoscd_remitos WHERE id_ingreso = %s ORDER BY id_remito',
                (id_ingreso,)
            )
            return cursor.fetchall()

    def get_recepciones_por_remito(self, id_remito: int) -> list[dict]:
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                'SELECT * FROM ingresoscd_remito_recepciones WHERE id_remito = %s ORDER BY id',
                (id_remito,)
            )
            return cursor.fetchall()

    def get_ingreso_completo(self, id_ingreso: str) -> dict | None:
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM ingresoscd WHERE id_ingreso = %s', (id_ingreso,))
            row_ingreso = cursor.fetchone()
            if not row_ingreso:
                return None
            cursor.execute(
                'SELECT * FROM ingresoscd_remitos WHERE id_ingreso = %s ORDER BY id_remito',
                (id_ingreso,)
            )
            rows_remitos = cursor.fetchall()
            for rem in rows_remitos:
                cursor.execute(
                    'SELECT * FROM ingresoscd_remito_recepciones WHERE id_remito = %s ORDER BY id',
                    (rem['id_remito'],)
                )
                rem['recepciones'] = cursor.fetchall()
        return {'ingreso': row_ingreso, 'remitos': rows_remitos}

    def delete_ingreso(self, id_ingreso: str):
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute('''
                DELETE rrc FROM ingresoscd_remito_recepciones rrc
                INNER JOIN ingresoscd_remitos rr ON rrc.id_remito = rr.id_remito
                WHERE rr.id_ingreso = %s
            ''', (id_ingreso,))
            cursor.execute(
                'DELETE FROM ingresoscd_remitos WHERE id_ingreso = %s',
                (id_ingreso,)
            )
            cursor.execute(
                'DELETE FROM ingresoscd WHERE id_ingreso = %s',
                (id_ingreso,)
            )

    def sincronizar_nombres_destino(self, ss_conn) -> dict:
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT DISTINCT sucursal_destino FROM ingresoscd_remito_recepciones "
                "WHERE nombre_destino = '' OR nombre_destino IS NULL"
            )
            sucursales = [r['sucursal_destino'] for r in cursor.fetchall()]
        actualizados = 0
        no_encontrados = 0
        for suc in sucursales:
            datos = ss_conn.obtener_datos_cliente(suc)
            if not datos or not datos['nombre']:
                no_encontrados += 1
                continue
            conn2 = self.connect()
            with conn2.cursor() as cur:
                cur.execute(
                    "UPDATE ingresoscd_remito_recepciones "
                    "SET nombre_destino = %s, domicilio_cliente = %s, "
                    "    codigo_postal_cliente = %s, ciudad_cliente = %s, "
                    "    distrito_cliente = %s "
                    "WHERE sucursal_destino = %s "
                    "AND (nombre_destino = '' OR nombre_destino IS NULL)",
                    (datos['nombre'], datos['domicilio'], datos['codigo_postal'],
                     datos['ciudad'], datos['distrito'], suc)
                )
                actualizados += cur.rowcount
        return {'actualizados': actualizados, 'no_encontrados': no_encontrados, 'total_sucursales': len(sucursales)}

    def sincronizar_razon_social_proveedores(self, ss_conn) -> dict:
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                "SELECT DISTINCT num_proveedor FROM ingresoscd "
                "WHERE razon_social = '' OR razon_social IS NULL"
            )
            proveedores = [r['num_proveedor'] for r in cursor.fetchall()]
        actualizados = 0
        no_encontrados = 0
        for prov in proveedores:
            datos = ss_conn.obtener_datos_proveedor(prov)
            if not datos or not datos['nombre']:
                no_encontrados += 1
                continue
            conn2 = self.connect()
            with conn2.cursor() as cur:
                cur.execute(
                    "UPDATE ingresoscd SET razon_social = %s WHERE num_proveedor = %s "
                    "AND (razon_social = '' OR razon_social IS NULL)",
                    (datos['nombre'], prov)
                )
                actualizados += cur.rowcount
        return {'actualizados': actualizados, 'no_encontrados': no_encontrados, 'total_proveedores': len(proveedores)}

    # ------------------------------------------------------------------
    # Hojas de ruta
    # Estados de hoja: 1 En preparación, 2 Despachada, 9 Anulada.
    # Estados de remito generado: 1 Emitido, 2 En Muelle, 3 Despachado.
    # ------------------------------------------------------------------

    @staticmethod
    def _sql_detalle_remitos_generados(extra_select: str = '', extra_join: str = '') -> str:
        """SELECT de remitos generados con proveedor, bultos y datos del destinatario."""
        return f'''
            SELECT g.id AS id_remito_generado, g.id_ingreso, g.num_remito,
                   g.destino AS sucursal_destino, g.fecha_generacion, g.estado,
                   i.fecha_ingreso, i.num_proveedor, i.razon_social,
                   COALESCE(b.total_bultos, 0) AS total_bultos,
                   COALESCE(b.nombre_destino, '') AS nombre_destino,
                   COALESCE(b.domicilio_cliente, '') AS domicilio_cliente,
                   COALESCE(b.codigo_postal_cliente, '') AS codigo_postal_cliente,
                   COALESCE(b.ciudad_cliente, '') AS ciudad_cliente,
                   COALESCE(b.distrito_cliente, '') AS distrito_cliente,
                   COALESCE(b.transporte_descripcion, '') AS transporte_descripcion
                   {extra_select}
            FROM ingresoscd_remitos_generados g
            INNER JOIN ingresoscd i ON i.id_ingreso = g.id_ingreso
            {extra_join}
            LEFT JOIN (
                SELECT t.id_ingreso, t.sucursal_destino,
                       SUM(t.cantidad_bultos) AS total_bultos,
                       MAX(t.nombre_destino) AS nombre_destino,
                       MAX(t.domicilio_cliente) AS domicilio_cliente,
                       MAX(t.codigo_postal_cliente) AS codigo_postal_cliente,
                       MAX(t.ciudad_cliente) AS ciudad_cliente,
                       MAX(t.distrito_cliente) AS distrito_cliente,
                       MAX(t.transporte_descripcion) AS transporte_descripcion
                FROM (
                    SELECT r.id_remito, r.id_ingreso, r.cantidad_bultos, rr.sucursal_destino,
                           MAX(rr.nombre_destino) AS nombre_destino,
                           MAX(rr.domicilio_cliente) AS domicilio_cliente,
                           MAX(rr.codigo_postal_cliente) AS codigo_postal_cliente,
                           MAX(rr.ciudad_cliente) AS ciudad_cliente,
                           MAX(rr.distrito_cliente) AS distrito_cliente,
                           MAX(rr.transporte_descripcion) AS transporte_descripcion
                    FROM ingresoscd_remitos r
                    INNER JOIN ingresoscd_remito_recepciones rr ON rr.id_remito = r.id_remito
                    GROUP BY r.id_remito, r.id_ingreso, r.cantidad_bultos, rr.sucursal_destino
                ) t
                GROUP BY t.id_ingreso, t.sucursal_destino
            ) b ON b.id_ingreso = g.id_ingreso AND b.sucursal_destino = g.destino
        '''

    def get_remitos_pendientes_despacho(self, id_hoja: int | None = None) -> list[dict]:
        """Remitos generados sin despachar y fuera de toda hoja de ruta activa.

        Si se indica id_hoja, incluye además los remitos que ya forman parte
        de esa hoja (para poder editarla).
        """
        sql = self._sql_detalle_remitos_generados() + '''
            WHERE (g.estado IN (1, 2) AND NOT EXISTS (
                      SELECT 1 FROM ingresoscd_hoja_ruta_remitos hr
                      INNER JOIN ingresoscd_hojas_ruta h ON h.id_hoja = hr.id_hoja
                      WHERE hr.id_remito_generado = g.id AND h.estado <> 9))
        '''
        params: list = []
        if id_hoja is not None:
            sql += '''
               OR g.id IN (SELECT id_remito_generado FROM ingresoscd_hoja_ruta_remitos
                           WHERE id_hoja = %s)
            '''
            params.append(id_hoja)
        sql += ' ORDER BY g.destino, g.num_remito'
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_remitos_de_hojas(self, ids_hoja: list[int]) -> dict[int, list[dict]]:
        if not ids_hoja:
            return {}
        fmt = ','.join(['%s'] * len(ids_hoja))
        sql = self._sql_detalle_remitos_generados(
            extra_select=', hr.id_hoja, hr.estado_previo',
            extra_join='INNER JOIN ingresoscd_hoja_ruta_remitos hr ON hr.id_remito_generado = g.id',
        ) + f' WHERE hr.id_hoja IN ({fmt}) ORDER BY g.destino, g.num_remito'
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, ids_hoja)
            rows = cursor.fetchall()
        result: dict[int, list[dict]] = {}
        for r in rows:
            result.setdefault(r['id_hoja'], []).append(r)
        return result

    def get_hojas_ruta(self, fecha_desde=None, fecha_hasta=None, estado: int | None = None) -> list[dict]:
        sql = 'SELECT * FROM ingresoscd_hojas_ruta'
        where, params = [], []
        if fecha_desde is not None:
            where.append('fecha_despacho >= %s')
            params.append(fecha_desde)
        if fecha_hasta is not None:
            where.append('fecha_despacho <= %s')
            params.append(fecha_hasta)
        if estado is not None:
            where.append('estado = %s')
            params.append(estado)
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY id_hoja DESC'
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def get_hoja_ruta(self, id_hoja: int) -> dict | None:
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('SELECT * FROM ingresoscd_hojas_ruta WHERE id_hoja = %s', (id_hoja,))
            return cursor.fetchone()

    def get_remitos_en_otra_hoja(self, ids_remito_generado: list[int],
                                 id_hoja_excluida: int | None = None) -> list[dict]:
        """Remitos de la lista que ya están en otra hoja de ruta no anulada."""
        if not ids_remito_generado:
            return []
        fmt = ','.join(['%s'] * len(ids_remito_generado))
        sql = (
            'SELECT g.num_remito, g.destino, h.id_hoja '
            'FROM ingresoscd_hoja_ruta_remitos hr '
            'INNER JOIN ingresoscd_hojas_ruta h ON h.id_hoja = hr.id_hoja '
            'INNER JOIN ingresoscd_remitos_generados g ON g.id = hr.id_remito_generado '
            f'WHERE h.estado <> 9 AND hr.id_remito_generado IN ({fmt})'
        )
        params: list = list(ids_remito_generado)
        if id_hoja_excluida is not None:
            sql += ' AND h.id_hoja <> %s'
            params.append(id_hoja_excluida)
        conn = self.connect()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def insert_hoja_ruta(self, fecha_despacho, transportista: str, chofer: str,
                         patente: str, observaciones: str) -> int:
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'INSERT INTO ingresoscd_hojas_ruta '
                '(fecha_despacho, transportista, chofer, patente, observaciones, estado) '
                'VALUES (%s, %s, %s, %s, %s, 1)',
                (fecha_despacho, transportista, chofer, patente, observaciones)
            )
            return cursor.lastrowid

    def update_hoja_ruta(self, id_hoja: int, fecha_despacho, transportista: str, chofer: str,
                         patente: str, observaciones: str) -> int:
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE ingresoscd_hojas_ruta SET fecha_despacho = %s, transportista = %s, '
                'chofer = %s, patente = %s, observaciones = %s '
                'WHERE id_hoja = %s AND estado = 1',
                (fecha_despacho, transportista, chofer, patente, observaciones, id_hoja)
            )
            return cursor.rowcount

    def reemplazar_remitos_hoja(self, id_hoja: int, ids_remito_generado: list[int]):
        """Deja en la hoja exactamente los remitos indicados (guarda su estado actual)."""
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM ingresoscd_hoja_ruta_remitos WHERE id_hoja = %s', (id_hoja,))
            if ids_remito_generado:
                fmt = ','.join(['%s'] * len(ids_remito_generado))
                cursor.execute(
                    'INSERT INTO ingresoscd_hoja_ruta_remitos '
                    '(id_hoja, id_remito_generado, estado_previo) '
                    f'SELECT %s, id, estado FROM ingresoscd_remitos_generados WHERE id IN ({fmt})',
                    [id_hoja, *ids_remito_generado]
                )

    def confirmar_despacho_hoja(self, id_hoja: int) -> bool:
        """Marca la hoja como Despachada y sus remitos como Despachados."""
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE ingresoscd_hojas_ruta SET estado = 2, despachado = NOW() '
                'WHERE id_hoja = %s AND estado = 1',
                (id_hoja,)
            )
            if cursor.rowcount != 1:
                return False
            cursor.execute(
                'UPDATE ingresoscd_remitos_generados g '
                'INNER JOIN ingresoscd_hoja_ruta_remitos hr ON hr.id_remito_generado = g.id '
                'SET g.estado = 3 WHERE hr.id_hoja = %s',
                (id_hoja,)
            )
            return True

    def anular_hoja_ruta(self, id_hoja: int) -> bool:
        """Anula la hoja; si estaba despachada, devuelve los remitos a su estado previo."""
        conn = self.connect()
        with conn.cursor() as cursor:
            cursor.execute(
                'UPDATE ingresoscd_remitos_generados g '
                'INNER JOIN ingresoscd_hoja_ruta_remitos hr ON hr.id_remito_generado = g.id '
                'INNER JOIN ingresoscd_hojas_ruta h ON h.id_hoja = hr.id_hoja '
                'SET g.estado = hr.estado_previo '
                'WHERE hr.id_hoja = %s AND h.estado = 2 AND g.estado = 3',
                (id_hoja,)
            )
            cursor.execute(
                'UPDATE ingresoscd_hojas_ruta SET estado = 9 '
                'WHERE id_hoja = %s AND estado IN (1, 2)',
                (id_hoja,)
            )
            return cursor.rowcount == 1
