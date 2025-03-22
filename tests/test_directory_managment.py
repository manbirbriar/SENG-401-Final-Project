import sys
from unittest.mock import patch

sys.path.append('imageprocessor/src')

from directory_management import *

#test generate_persist_dir

@patch("os.name", "nt") 
@patch("os.path.expanduser", return_value="C:\\Users\\TestUser")  
def test_generate_persist_dir_windows(mock_expanduser):
    persist_dir = generate_persist_dir()

    assert persist_dir == "C:\\Users\\TestUser\\AppData\\Local\\AI RAW Image Processor", "Incorrect persist directory path"


@patch("os.name", "posix")  
@patch("os.path.expanduser", return_value="/home/testuser")  
def test_generate_persist_dir_posix(mock_expanduser):
    persist_dir = generate_persist_dir()

    assert persist_dir == "/home/testuser/.config/AI RAW Image Processor", "Incorrect path for macOS/Linux"

#test create_persist_dir

@patch("directory_management.generate_persist_dir", return_value="C:\\Users\\TestUser\\AppData\\Local\\AI RAW Image Processor")
@patch("os.makedirs")  
@patch("os.path.exists", side_effect=lambda path: False if "thumbnails" in path else True)  # Mock os.path.exists
def test_create_persist_dir_partial_exists(mock_exists, mock_makedirs, mock_generate_persist_dir):
    persist_dir = create_persist_dir()

    assert persist_dir == "C:\\Users\\TestUser\\AppData\\Local\\AI RAW Image Processor", "Incorrect persist directory path"


@patch("directory_management.generate_persist_dir", return_value="/home/testuser/.config/AI RAW Image Processor")
@patch("os.makedirs")  
@patch("os.path.exists", return_value=False)  
def test_create_persist_dir_all_missing(mock_exists, mock_makedirs, mock_generate_persist_dir):
    persist_dir = create_persist_dir()

    assert persist_dir == "/home/testuser/.config/AI RAW Image Processor", "Incorrect persist directory path"
    assert mock_makedirs.call_count == 2, "os.makedirs should be called twice (for main dir and thumbnails)"


@patch("directory_management.generate_persist_dir", return_value="/home/testuser/.config/AI RAW Image Processor")
@patch("os.makedirs")  
@patch("os.path.exists", return_value=True)  
def test_create_persist_dir_all_exist(mock_exists, mock_makedirs, mock_generate_persist_dir):
    persist_dir = create_persist_dir()

    assert persist_dir == "/home/testuser/.config/AI RAW Image Processor", "Incorrect persist directory path"

#test generate_temp_dir

@patch("tempfile.gettempdir", return_value="\\tmp")  
def test_generate_temp_dir(mock_gettempdir):
    temp_dir = generate_temp_dir()

    assert temp_dir == "\\tmp\\AI RAW Image Processor", "incorrect temporary directory"

#test create_temp_dir

@patch("directory_management.generate_temp_dir", return_value="\\tmp\\AI RAW Image Processor")
@patch("os.makedirs")  
@patch("os.path.exists", return_value=False)  
def test_create_temp_dir_missing(mock_exists, mock_makedirs, mock_generate_temp_dir):
    temp_dir = create_temp_dir()

    assert temp_dir == "\\tmp\\AI RAW Image Processor", "Incorrect temporary directory path"


@patch("directory_management.generate_temp_dir", return_value="\\tmp\\AI RAW Image Processor")
@patch("os.makedirs")  
@patch("os.path.exists", return_value=True)  
def test_create_temp_dir_exists(mock_exists, mock_makedirs, mock_generate_temp_dir):
    temp_dir = create_temp_dir()

    assert temp_dir == "\\tmp\\AI RAW Image Processor", "Incorrect temporary directory path"