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
