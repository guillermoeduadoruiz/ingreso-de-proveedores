import sys
import os

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication

from config.config_manager import ConfigManager
from ui.ventana_principal import VentanaPrincipal
from ui.login_dialog import LoginDialog


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('Registro de Ingreso de Mercadería')
    app.setOrganizationName('Logistica')

    cm = ConfigManager()
    cm.load_config()

    login_dlg = LoginDialog(cm.sqlserver)
    if login_dlg.exec_() != LoginDialog.Accepted:
        sys.exit(0)

    window = VentanaPrincipal(cm)
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
