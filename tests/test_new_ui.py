import sys
import pytest
import numpy as np
from PIL import Image
import os

sys.path.append('imageprocessor/src')

from main import create_control_area
from ImageProcessing import RawImage, Parameter

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
sample_image_path = os.path.join(current_dir, '../sample_images/R62_0323.CR3')


import flet as ft

def test_create_control_area():
    class MockPage:
        def update(self):
            pass  # Mock the update method to do nothing

    # Create a mock page object
    mock_page = MockPage()

    # Call the function with the mock page
    results = create_control_area(mock_page)
    
    # Unpack returned components
    status_text_box, status_container, prompt_text_box, feedback_text_box, submit_button, compare_button, apply_button = results

    assert isinstance(status_text_box, ft.Text), "Status text box should be an instance of ft.Text"
    assert isinstance(status_container, ft.Row), "Status container should be an instance of ft.Row"
    assert isinstance(prompt_text_box, ft.TextField), "Prompt text box should be an instance of ft.TextField"
    assert isinstance(feedback_text_box, ft.Text), "Feedback text box should be an instance of ft.Text"
    assert isinstance(submit_button, ft.TextButton), "Submit button should be an instance of ft.TextButton"
    assert isinstance(compare_button, ft.TextButton), "Compare button should be an instance of ft.TextButton"
    assert isinstance(apply_button, ft.TextButton), "Apply button should be an instance of ft.TextButton"
    assert prompt_text_box.label == 'Prompt', "Prompt text box label should be 'Prompt'"
    assert prompt_text_box.multiline is True, "Prompt text box should be multiline"
    assert status_text_box.value == 'Ready', "Initial text of status text box should be 'Ready'"


def test_adjust_exposure():
    dummy_image = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float32)
    result = RawImage.adjust_exposure(dummy_image, 1)  # Increase exposure by 1 stop
    expected = np.array([[1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    assert np.array_equal(result, expected), "Exposure adjustment does not match expected result"


def test_adjust_contrast():
    dummy_image = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float32)
    result = RawImage.adjust_contrast(dummy_image, 100)  # Increase contrast by 100%
    expected = np.array([[0.583, 0.583], [0.583, 0.583]], dtype=np.float32)
    assert np.allclose(result, expected, rtol=1e-3, atol=1e-3), "Contrast adjustment does not match expected result"

def test_init_():
    params = Parameter()
    assert params.exposure == 0, "Default exposure should be 0"
    assert params.contrast == 0, "Default contrast should be 0"
    custom_params = Parameter(exposure=2, contrast=10)
    assert custom_params.exposure == 2, "Custom exposure should be 2"
    assert custom_params.contrast == 10, "Custom contrast should be 10"

def test_render_image():
    class MockParams:
        exposure = 1
        contrast = 50

    raw = RawImage(sample_image_path)
    params = MockParams()
    rendered_image = raw.render_image(params)
    assert isinstance(rendered_image, np.ndarray), "Rendered image should be a NumPy array"
    assert rendered_image.shape == raw.raw_image.shape, "Rendered image should have the same shape as the raw image"


def test_srgb_gamma_correction():
    dummy_image = np.array([[0.1, 0.5], [0.9, 1.0]], dtype=np.float32)
    corrected_image = RawImage.srgb_gamma_correction(dummy_image)
    assert isinstance(corrected_image, np.ndarray), "Gamma-corrected image should be a NumPy array"
    assert corrected_image.shape == dummy_image.shape, "Gamma-corrected image should have the same shape as the input"
    assert np.all(corrected_image >= 0) and np.all(corrected_image <= 1), "Gamma-corrected values should be in range [0, 1]"


def test_save_image(tmp_path):
    dummy_image = np.random.rand(100, 100, 3).astype(np.float32)
    save_path = tmp_path / "test_image.png"
    RawImage.save_image(dummy_image, str(save_path))
    assert save_path.exists(), "Image file should be saved"
    saved_image = Image.open(save_path)
    assert saved_image.size == (100, 100), "Saved image should have the correct dimensions"
    assert saved_image.mode == "RGB", "Saved image should be in RGB mode"


