import hashlib
import pyodbc
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from database.conexiones import ConfigSQLServer


class LoginDialog(QDialog):
    def __init__(self, sqlserver_config: ConfigSQLServer, parent=None):
        super().__init__(parent)
        self._config = sqlserver_config
        self._user_info: dict | None = None
        self.setWindowTitle('Inicio de sesión')
        self.setFixedSize(420, 320)
        self.setModal(True)
        self.setStyleSheet(self._dialog_styles())
        self._setup_ui()

    def _dialog_styles(self):
        return '''
            QDialog {
                background-color: #f0f2f5;
            }
            QLineEdit {
                padding: 10px 12px;
                border: 2px solid #d1d5db;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #2563eb;
            }
            QPushButton#btnIngresar {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 32px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#btnIngresar:hover {
                background-color: #1d4ed8;
            }
            QPushButton#btnIngresar:disabled {
                background-color: #93c5fd;
            }
            QPushButton#btnCancelar {
                background-color: transparent;
                color: #6b7280;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                padding: 10px 24px;
                font-size: 14px;
            }
            QPushButton#btnCancelar:hover {
                background-color: #f3f4f6;
            }
            QPushButton#btnOjo {
                background-color: transparent;
                border: none;
                font-size: 18px;
                padding: 4px 8px;
                color: #9ca3af;
            }
            QPushButton#btnOjo:hover {
                color: #4b5563;
            }
        '''

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel('Registro de Ingreso de Proveedores')
        header.setAlignment(Qt.AlignCenter)
        header.setFixedHeight(60)
        header.setStyleSheet('''
            background-color: #2563eb;
            color: white;
            font-size: 16px;
            font-weight: bold;
            padding: 16px;
        ''')
        layout.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(32, 24, 32, 24)
        body.setSpacing(16)

        subtitle = QLabel('Ingrese sus credenciales de Cygnus')
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('color: #6b7280; font-size: 13px;')
        body.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)

        self.txt_usuario = QLineEdit()
        self.txt_usuario.setPlaceholderText('Ingrese su usuario')
        self.txt_usuario.setMaxLength(20)
        form.addRow('Usuario:', self.txt_usuario)

        pass_layout = QHBoxLayout()
        pass_layout.setSpacing(4)
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setPlaceholderText('Ingrese su contraseña')
        pass_layout.addWidget(self.txt_password)

        self.btn_ojo = QPushButton('\U0001F441')
        self.btn_ojo.setObjectName('btnOjo')
        self.btn_ojo.setToolTip('Mostrar / Ocultar contraseña')
        self.btn_ojo.setFixedWidth(36)
        self._password_visible = False
        self.btn_ojo.clicked.connect(self._toggle_password)
        pass_layout.addWidget(self.btn_ojo)

        form.addRow('Contraseña:', pass_layout)

        body.addLayout(form)

        self.lbl_error = QLabel('')
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setStyleSheet('color: #dc2626; font-weight: bold; font-size: 12px;')
        body.addWidget(self.lbl_error)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        self.btn_cancelar = QPushButton('Cancelar')
        self.btn_cancelar.setObjectName('btnCancelar')
        self.btn_ingresar = QPushButton('Ingresar')
        self.btn_ingresar.setObjectName('btnIngresar')
        self.btn_ingresar.setDefault(True)

        buttons.addStretch()
        buttons.addWidget(self.btn_cancelar)
        buttons.addWidget(self.btn_ingresar)
        body.addLayout(buttons)

        layout.addLayout(body)
        layout.addStretch()

        self.btn_cancelar.clicked.connect(self.reject)
        self.btn_ingresar.clicked.connect(self._ingresar)
        self.txt_password.returnPressed.connect(self._ingresar)

        QTimer.singleShot(100, self.txt_usuario.setFocus)

        self.txt_usuario.setFocus()

    def _toggle_password(self):
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.txt_password.setEchoMode(QLineEdit.Normal)
        else:
            self.txt_password.setEchoMode(QLineEdit.Password)

    def _ingresar(self):
        usuario = self.txt_usuario.text().strip()
        password = self.txt_password.text()

        if not usuario:
            self.lbl_error.setText('Debe ingresar un usuario.')
            self.txt_usuario.setFocus()
            return

        if not password:
            self.lbl_error.setText('Debe ingresar una contraseña.')
            self.txt_password.setFocus()
            return

        self.btn_ingresar.setEnabled(False)
        self.lbl_error.setText('')

        if not self._config.server or not self._config.database:
            self.lbl_error.setText(
                'Base de datos no configurada.\n'
                'Ejecute el configurador antes de usar la aplicación.'
            )
            self.btn_ingresar.setEnabled(True)
            return

        try:
            # MD5 requerido por el WMS (Cygnus) — no se puede cambiar sin modificar el sistema externo
            clave_hash = hashlib.md5((usuario + password).encode('utf-8')).hexdigest().upper()

            if self._config.trusted:
                conn_str = (
                    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                    f'SERVER={self._config.server};'
                    f'DATABASE={self._config.database};'
                    f'Trusted_Connection=yes;'
                )
            else:
                conn_str = (
                    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
                    f'SERVER={self._config.server};'
                    f'DATABASE={self._config.database};'
                    f'UID={self._config.username};'
                    f'PWD={self._config.password};'
                )

            conn = pyodbc.connect(conn_str, timeout=5)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT IdUsuario, Apellido, Nombres, DescripcionCorta, Email
                FROM SecUsuarios WITH (NOLOCK)
                WHERE IdUsuario = ? AND Clave = ? AND ISNULL(StatusRegistro, '') != 'B'
            ''', (usuario, clave_hash))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                self._user_info = {
                    'IdUsuario': row.IdUsuario,
                    'Apellido': row.Apellido,
                    'Nombres': row.Nombres,
                    'DescripcionCorta': row.DescripcionCorta,
                    'Email': row.Email,
                }
                self.accept()
            else:
                self.lbl_error.setText('Usuario o contraseña incorrectos.')
                self.txt_password.selectAll()
                self.txt_password.setFocus()

        except pyodbc.Error as e:
            self.lbl_error.setText(f'Error de conexión: {str(e)[:80]}')
        except Exception as e:
            self.lbl_error.setText(f'Error inesperado: {str(e)[:80]}')
        finally:
            self.btn_ingresar.setEnabled(True)

    @property
    def user_info(self) -> dict | None:
        return self._user_info
