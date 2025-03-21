import sys
import pytest
import numpy as np
from PIL import Image
import os
import flet as ft
import rawpy
from unittest.mock import Mock, patch


sys.path.append('imageprocessor/src')

from main import create_control_area
from ImageProcessing import RawImage, Parameter, EmptyImage, ImageProcessorThread

#Parameter Tests

def test_Parameter_init_default():
    param = Parameter()

    assert isinstance(param, Parameter), "Object should be an instance of Parameter"
    assert param.exposure == 0, "Default exposure should be 0"
    assert param.contrast == 0, "Default contrast should be 0"
    assert param.highlights == 0, "Default highlights should be 0"
    assert param.shadows == 0, "Default shadows should be 0"
    assert param.black_levels == 0, "Default black_levels should be 0"


def test_Parameter_init_custom():
    param = Parameter(exposure=2, contrast=10, highlights=3, shadows=-2, black_levels=1)

    assert isinstance(param, Parameter), "Object should be an instance of Parameter"
    assert param.exposure == 2, "Custom exposure should be 2"
    assert param.contrast == 10, "Custom contrast should be 10"
    assert param.highlights == 3, "Custom highlights should be 3"
    assert param.shadows == -2, "Custom shadows should be -2"
    assert param.black_levels == 1, "Custom black_levels should be 1"

#RawImage Tests
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
sample_image_path = os.path.join(current_dir, '../sample_images/R62_0323.CR3')


def test_RawImage_init():
    raw = RawImage(sample_image_path)
    assert isinstance(raw, RawImage)
    assert isinstance(raw.raw_image, np.ndarray)

def test_RawImage_adjust_exposure():
    dummy_image = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float32)
    result = RawImage.adjust_exposure(dummy_image, 1)  # Increase exposure by 1 stop
    expected = np.array([[1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    assert np.array_equal(result, expected), "Exposure adjustment does not match expected result"


def test_RawImage_adjust_contrast():
    dummy_image = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float32)
    result = RawImage.adjust_contrast(dummy_image, 100)  # Increase contrast by 100
    contrast = 100 / 800 + 1  # Updated contrast calculation
    pivot = 0.416
    expected = (dummy_image - pivot) * contrast + pivot
    assert np.allclose(result, expected, rtol=1e-3, atol=1e-3), "Contrast adjustment does not match expected result"

def test_RawImage_srgb_gamma_correction():
    dummy_image = np.array([[0.1, 0.5], [0.9, 1.0]], dtype=np.float32)
    corrected_image = RawImage.srgb_gamma_correction(dummy_image)
    assert isinstance(corrected_image, np.ndarray), "Gamma-corrected image should be a NumPy array"
    assert corrected_image.shape == dummy_image.shape, "Gamma-corrected image should have the same shape as the input"
    assert np.all(corrected_image >= 0) and np.all(corrected_image <= 1), "Gamma-corrected values should be in range [0, 1]"


def test_RawImage_save_image(tmp_path):
    dummy_image = np.random.rand(100, 100, 3).astype(np.float32)
    save_path = tmp_path / "test_image.png"
    RawImage.save_image(dummy_image, str(save_path))
    assert save_path.exists(), "Image file should be saved"
    saved_image = Image.open(save_path)
    assert saved_image.size == (100, 100), "Saved image should have the correct dimensions"
    assert saved_image.mode == "RGB", "Saved image should be in RGB mode"

#EmptyImage Test 

def test_EmptyImage():
    empty = EmptyImage()

    assert isinstance(empty, EmptyImage)
    assert isinstance(empty.raw_image, np.ndarray)

def test_EmptyImage_adjust_exposure():
    dummy_image = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float32)
    result = EmptyImage.adjust_exposure(dummy_image, 1)  # Increase exposure by 1 stop
    expected = np.array([[1.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    assert np.array_equal(result, expected), "Exposure adjustment does not match expected result"


def test_EmptyImage_adjust_contrast():
    dummy_image = np.array([[0.5, 0.5], [0.5, 0.5]], dtype=np.float32)
    result = EmptyImage.adjust_contrast(dummy_image, 100)  # Increase contrast by 100
    contrast = 100 / 800 + 1  # Updated contrast calculation
    pivot = 0.416
    expected = (dummy_image - pivot) * contrast + pivot
    assert np.allclose(result, expected, rtol=1e-3, atol=1e-3), "Contrast adjustment does not match expected result"

def test_EmptyImage_srgb_gamma_correction():
    dummy_image = np.array([[0.1, 0.5], [0.9, 1.0]], dtype=np.float32)
    corrected_image = EmptyImage.srgb_gamma_correction(dummy_image)
    assert isinstance(corrected_image, np.ndarray), "Gamma-corrected image should be a NumPy array"
    assert corrected_image.shape == dummy_image.shape, "Gamma-corrected image should have the same shape as the input"
    assert np.all(corrected_image >= 0) and np.all(corrected_image <= 1), "Gamma-corrected values should be in range [0, 1]"


def test_EmptyImage_save_image(tmp_path):
    dummy_image = np.random.rand(100, 100, 3).astype(np.float32)
    save_path = tmp_path / "test_image.png"
    EmptyImage.save_image(dummy_image, str(save_path))
    assert save_path.exists(), "Image file should be saved"
    saved_image = Image.open(save_path)
    assert saved_image.size == (100, 100), "Saved image should have the correct dimensions"
    assert saved_image.mode == "RGB", "Saved image should be in RGB mode"    

#ImageProcessorThread Test

@patch("ImageProcessing.TEMP_DIR", "/tmp")  # Mock TEMP_DIR for testing
def test_ImageProcessorThread_initialization():
    thread1 = ImageProcessorThread()
    assert isinstance(thread1, ImageProcessorThread), "Thread should be an instance of ImageProcessorThread"
    assert not thread1.event.is_set(), "Event should not be set initially"
    assert not thread1.need_update_image, "need_update_image should be False initially"
    assert not thread1.generate_original, "generate_original should be False initially"

    thread2 = ImageProcessorThread()
    assert thread1 is thread2, "ImageProcessorThread should enforce singleton behavior"


