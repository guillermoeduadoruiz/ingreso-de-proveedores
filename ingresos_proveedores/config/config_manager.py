import json
import os
import sys
from dataclasses import asdict

if not getattr(sys, 'frozen', False):
    _PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _PKG_DIR not in sys.path:
        sys.path.insert(0, _PKG_DIR)

from database.conexiones import ConfigSQLServer, ConfigMySQL, ConfigImpresoras, ConfigImpresion
from utils.crypto import hash_password, verify_password, encrypt_password, decrypt_password
from utils.paths import config_path as _config_path


class ConfigManager:
    def __init__(self):
        self.sqlserver = ConfigSQLServer()
        self.mysql = ConfigMySQL()
        self.impresoras_configs: dict[str, ConfigImpresoras] = {}
        self.impresora_activa: str = ''
        self.impresion = ConfigImpresion()
        self.clave_anulacion: str = ''
        self._loaded = False

    def _get_config_path(self) -> str:
        return _config_path()

    def _get_password_file(self) -> str:
        appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
        folder = os.path.join(appdata, 'IngresosProveedores')
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, '.config_pass')

    @property
    def impresoras(self) -> ConfigImpresoras:
        if self.impresora_activa in self.impresoras_configs:
            return self.impresoras_configs[self.impresora_activa]
        default = ConfigImpresoras()
        self.impresoras_configs['Default'] = default
        self.impresora_activa = 'Default'
        return default

    def get_printer_config_names(self) -> list[str]:
        return list(self.impresoras_configs.keys())

    def get_printer_config(self, name: str) -> ConfigImpresoras | None:
        return self.impresoras_configs.get(name)

    def save_printer_config(self, config: ConfigImpresoras, name: str | None = None):
        target = name or self.impresora_activa
        if not target:
            target = 'Default'
            self.impresora_activa = 'Default'
        self.impresoras_configs[target] = config
        self.impresora_activa = target
        self._save_to_file()

    def delete_printer_config(self, name: str):
        if name in self.impresoras_configs and len(self.impresoras_configs) > 1:
            del self.impresoras_configs[name]
            if self.impresora_activa == name:
                self.impresora_activa = next(iter(self.impresoras_configs))
            self._save_to_file()

    def rename_printer_config(self, old_name: str, new_name: str):
        if old_name in self.impresoras_configs and new_name not in self.impresoras_configs:
            self.impresoras_configs[new_name] = self.impresoras_configs.pop(old_name)
            if self.impresora_activa == old_name:
                self.impresora_activa = new_name
            self._save_to_file()

    def set_active_config(self, name: str):
        if name in self.impresoras_configs:
            self.impresora_activa = name
            self._save_to_file()

    def _config_to_dict(self, cfg: ConfigImpresoras) -> dict:
        d = asdict(cfg)
        return {k: v for k, v in d.items() if not k.startswith('_') and k.islower()}

    def _dict_to_config(self, d: dict) -> ConfigImpresoras:
        valid = {k: v for k, v in d.items() if hasattr(ConfigImpresoras, k)}
        return ConfigImpresoras(**valid)

    def load_config(self):
        if self._loaded:
            return
        self._loaded = True

        config_file = self._get_config_path()
        if not os.path.exists(config_file):
            return
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            ss = data.get('sqlserver', {})
            if ss.get('server') and ss.get('database'):
                ss = dict(ss)
                ss['password'] = decrypt_password(ss.get('password', ''))
                self.sqlserver = ConfigSQLServer(**ss)
            my = data.get('mysql', {})
            if my.get('host') and my.get('database'):
                my = dict(my)
                my['password'] = decrypt_password(my.get('password', ''))
                self.mysql = ConfigMySQL(**my)
            imp = data.get('impresoras', {})
            if imp:
                if 'configs' in imp:
                    cfg_dict = imp['configs']
                    for name, vals in cfg_dict.items():
                        self.impresoras_configs[name] = self._dict_to_config(vals)
                    self.impresora_activa = imp.get('activa', list(cfg_dict.keys())[0] if cfg_dict else '')
                else:
                    cfg = self._dict_to_config(imp)
                    self.impresoras_configs['Default'] = cfg
                    self.impresora_activa = 'Default'
            if not self.impresoras_configs:
                self.impresoras_configs['Default'] = ConfigImpresoras()
                self.impresora_activa = 'Default'

            imp = data.get('impresion', {})
            if imp:
                valid = {k: v for k, v in imp.items() if hasattr(ConfigImpresion, k)}
                self.impresion = ConfigImpresion(**valid)
            self.clave_anulacion = data.get('clave_anulacion', '')
        except Exception:
            pass

    def save_sqlserver_config(self, config: ConfigSQLServer):
        self.sqlserver = config
        self._save_to_file()

    def save_mysql_config(self, config: ConfigMySQL):
        self.mysql = config
        self._save_to_file()

    def save_impresion_config(self, config: ConfigImpresion):
        self.impresion = config
        self._save_to_file()

    def _save_to_file(self):
        config_file = self._get_config_path()
        try:
            configs_dict = {}
            for name, cfg in self.impresoras_configs.items():
                configs_dict[name] = self._config_to_dict(cfg)
            data = {
                'clave_anulacion': self.clave_anulacion,
                'sqlserver': {
                    'server': self.sqlserver.server,
                    'database': self.sqlserver.database,
                    'username': self.sqlserver.username,
                    'password': encrypt_password(self.sqlserver.password),
                    'trusted': self.sqlserver.trusted,
                },
                'mysql': {
                    'host': self.mysql.host,
                    'port': self.mysql.port,
                    'database': self.mysql.database,
                    'username': self.mysql.username,
                    'password': encrypt_password(self.mysql.password),
                },
                'impresoras': {
                    'configs': configs_dict,
                    'activa': self.impresora_activa,
                },
                'impresion': asdict(self.impresion),
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def password_setup_required(self) -> bool:
        return not os.path.exists(self._get_password_file())

    def setup_password(self, password: str):
        hashed = hash_password(password)
        with open(self._get_password_file(), 'w', encoding='utf-8') as f:
            f.write(hashed)

    def verify_password(self, password: str) -> bool:
        pass_file = self._get_password_file()
        if not os.path.exists(pass_file):
            return False
        with open(pass_file, 'r', encoding='utf-8') as f:
            stored = f.read().strip()
        return verify_password(password, stored)

    def change_password(self, old_password: str, new_password: str) -> bool:
        if not self.verify_password(old_password):
            return False
        self.setup_password(new_password)
        return True

    @property
    def is_configured(self) -> bool:
        return (
            bool(self.sqlserver.server and self.sqlserver.database)
            and bool(self.mysql.host and self.mysql.database)
        )

    @property
    def is_unlocked(self) -> bool:
        return True
