from datetime import datetime
import secrets
import string


def generar_id_ingreso() -> str:
    now = datetime.now()
    fecha = now.strftime('%Y%m%d')
    chars = string.ascii_uppercase + string.digits
    sufijo = ''.join(secrets.choice(chars) for _ in range(6))
    return f'ING-{fecha}-{sufijo}'
