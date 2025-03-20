import os
import tempfile

from config import APP_NAME


def generate_persist_dir():
    sys_win = os.name == 'nt'
    if sys_win:  # Windows
        persist_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", APP_NAME)
    else:  # macOS/Linux
        persist_dir = os.path.join(os.path.expanduser("~"), ".config", APP_NAME)
    return persist_dir


def create_persist_dir():
    persist_dir = generate_persist_dir()
    for i in (persist_dir, os.path.join(persist_dir, 'thumbnails')):
        if not os.path.exists(i):
            os.makedirs(i)
    return persist_dir


def generate_temp_dir():
    return os.path.join(tempfile.gettempdir(), APP_NAME)


def create_temp_dir():
    temp_dir = generate_temp_dir()
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir
