import os
import json
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


SALT_FILE = None
CONFIG_KEY = b'config_data'


def _get_salt_path():
    global SALT_FILE
    if SALT_FILE is None:
        app_data = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'IngresosProveedores')
        os.makedirs(app_data, exist_ok=True)
        SALT_FILE = os.path.join(app_data, '.salt')
    return SALT_FILE


def _load_or_create_salt():
    salt_path = _get_salt_path()
    if os.path.exists(salt_path):
        with open(salt_path, 'rb') as f:
            return f.read()
    salt = os.urandom(16)
    with open(salt_path, 'wb') as f:
        f.write(salt)
    return salt


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
    return key


def hash_password(password: str) -> str:
    salt = _load_or_create_salt()
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 600000)
    return base64.b64encode(salt + dk).decode('utf-8')


def verify_password(password: str, stored: str) -> bool:
    raw = base64.b64decode(stored.encode('utf-8'))
    salt = raw[:16]
    dk = raw[16:]
    new_dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 600000)
    return dk == new_dk


def encrypt_config(data: dict, password: str) -> str:
    salt = _load_or_create_salt()
    key = _derive_key(password, salt)
    f = Fernet(key)
    json_str = json.dumps(data, ensure_ascii=False)
    encrypted = f.encrypt(json_str.encode('utf-8'))
    return base64.b64encode(encrypted).decode('utf-8')


def decrypt_config(encrypted_b64: str, password: str) -> dict:
    salt = _load_or_create_salt()
    key = _derive_key(password, salt)
    f = Fernet(key)
    encrypted = base64.b64decode(encrypted_b64.encode('utf-8'))
    json_str = f.decrypt(encrypted).decode('utf-8')
    return json.loads(json_str)


def _get_machine_key() -> bytes:
    salt = _load_or_create_salt()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(b'IngresosProveedores_MasterKey_2024'))
    return key


ENC_PREFIX = '$ENC$'


def encrypt_password(password: str) -> str:
    if not password:
        return ''
    key = _get_machine_key()
    f = Fernet(key)
    encrypted = f.encrypt(password.encode('utf-8'))
    return ENC_PREFIX + base64.b64encode(encrypted).decode('utf-8')


def decrypt_password(encrypted_data: str) -> str:
    if not encrypted_data:
        return ''
    if not encrypted_data.startswith(ENC_PREFIX):
        return encrypted_data
    key = _get_machine_key()
    f = Fernet(key)
    raw = encrypted_data[len(ENC_PREFIX):]
    encrypted = base64.b64decode(raw.encode('utf-8'))
    return f.decrypt(encrypted).decode('utf-8')
