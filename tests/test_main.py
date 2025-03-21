import sys
import pytest
import numpy as np
from PIL import Image
import os
import flet as ft
import rawpy
from unittest.mock import Mock, patch

sys.path.append('imageprocessor/src')

from main import *
from ImageProcessing import RawImage, Parameter, EmptyImage, ImageProcessorThread

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
raw_path = os.path.join(current_dir, '../sample_images/R62_0323.CR3')

@pytest.fixture
def mock_page():
    page = Mock()
    page.width = 800
    page.height = 600  
    page.overlay = []  
    page.update = Mock()  
    return page



@pytest.fixture
def mock_params():
    return Parameter()

@pytest.fixture
def mock_image_processor_thread():
    thread = Mock(spec=ImageProcessorThread)
    return thread

#test create_photo_area

def test_create_photo_area_with_none_path(mock_page, mock_params, mock_image_processor_thread):
    raw_path = None
    image_object, img_container = create_photo_area(mock_page, raw_path, mock_params)

    assert isinstance(image_object, EmptyImage), "Expected image_object to be an instance of EmptyImage"
    assert img_container.width == mock_page.width, "Image container width should match page width"
    assert img_container.height == mock_page.height, "Image container height should match page height"

def test_create_photo_area_with_valid_path(mock_page, mock_params, mock_image_processor_thread, mocker):
    image_object, img_container = create_photo_area(mock_page, raw_path, mock_params)

    assert isinstance(image_object, RawImage), "Expected image_object to be an instance of RawImage"
    assert img_container.width == mock_page.width, "Image container width should match page width"
    assert img_container.height == mock_page.height, "Image container height should match page height"

#test create_control_area

def test_create_control_area(mock_page):
    status_text_box, status_container, prompt_text_box, feedback_text_box, submit_button, compare_button, reset_button = create_control_area(mock_page)

    assert isinstance(status_text_box, ft.Text), "status_text_box should be an instance of ft.Text"
    assert status_text_box.value == "Ready", "status_text_box should have the value 'Ready'"

    assert isinstance(status_container, ft.Row), "status_container should be an instance of ft.Row"
    assert len(status_container.controls) == 2, "status_container should have two controls"
    assert isinstance(status_container.controls[0], ft.Text), "First control in status_container should be an instance of ft.Text"
    assert isinstance(status_container.controls[1], ft.Text), "Second control in status_container should be an instance of ft.Text"

    assert isinstance(prompt_text_box, ft.TextField), "prompt_text_box should be an instance of ft.TextField"
    assert prompt_text_box.label == "Describe how you want to improve the image", "prompt_text_box should have the correct label"

    assert isinstance(feedback_text_box, ft.Text), "feedback_text_box should be an instance of ft.Text"

    assert isinstance(submit_button, ft.TextButton), "submit_button should be an instance of ft.TextButton"
    assert submit_button.text == "Submit", "submit_button should have the text 'Submit'"

    assert isinstance(compare_button, ft.TextButton), "compare_button should be an instance of ft.TextButton"
    assert compare_button.text == "Compare", "compare_button should have the text 'Compare'"
    assert compare_button.tooltip == "Click to toggle the original image and the edited one", "compare_button should have the correct tooltip"

    assert isinstance(reset_button, ft.TextButton), "reset_button should be an instance of ft.TextButton"
    assert reset_button.text == "Reset", "reset_button should have the text 'Reset'"

#test open_url

@patch("os.system")
@patch("os.name", "nt")
def test_open_url_windows(mock_os_system):
    url = "http://example.com"
    open_url(url)

    mock_os_system.assert_called_once_with(f"start {url}")


@patch("os.system")
@patch("os.name", "posix") 
def test_open_url_non_windows(mock_os_system):
    url = "http://example.com"
    open_url(url)

    mock_os_system.assert_called_once_with(f"open {url}")

