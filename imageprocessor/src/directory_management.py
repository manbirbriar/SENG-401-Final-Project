import os
import tempfile

from config import APP_NAME


def generate_persist_dir():
    """
    Generates the directory path for persistent application data storage.

    The directory location varies depending on the operating system:
    - On Windows, it is under the user's `AppData\Local` directory.
    - On macOS/Linux, it is under the user's `.config` directory.

    :return: The full path to the persistent storage directory.
    """
    sys_win = os.name == 'nt'
    if sys_win:  # Windows
        persist_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", APP_NAME)
    else:  # macOS/Linux
        persist_dir = os.path.join(os.path.expanduser("~"), ".config", APP_NAME)
    return persist_dir


def create_persist_dir():
    """
    Creates the persistent data directory if it does not already exist.

    This function creates the main directory for persistent storage, as well as
    a subdirectory called `thumbnails`. It uses `generate_persist_dir` to determine
    the location of the storage directory.

    :return: The path to the main persistent storage directory.
    """
    persist_dir = generate_persist_dir()
    for i in (persist_dir, os.path.join(persist_dir, 'thumbnails')):
        if not os.path.exists(i):
            os.makedirs(i)
    return persist_dir


def generate_temp_dir():
    """
    Generates the path to the temporary storage directory.

    This directory is created under the system's default temporary directory,
    with a subdirectory named after the application (`APP_NAME`).

    :return: The full path to the temporary storage directory.
    """
    return os.path.join(tempfile.gettempdir(), APP_NAME)


def create_temp_dir():
    """
    Creates the temporary storage directory if it does not already exist.

    This function ensures the temporary directory exists, created using `generate_temp_dir`.

    :return: The path to the temporary storage directory.
    """
    temp_dir = generate_temp_dir()
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    return temp_dir
