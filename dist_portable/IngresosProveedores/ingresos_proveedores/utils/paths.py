import os
import sys


def _is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def app_dir() -> str:
    if _is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def assets_dir() -> str:
    if _is_frozen():
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'assets')


def config_path() -> str:
    return os.path.join(app_dir(), 'config_setup.json')


def pdfs_dir() -> str:
    return os.path.join(app_dir(), 'pdfs')
