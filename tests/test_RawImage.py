import sys
import pytest
import numpy as np
from PIL import Image
import os
import flet as ft
import rawpy


sys.path.append('imageprocessor/src')

from main import create_control_area
from ImageProcessing import RawImage, Parameter
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
sample_image_path = os.path.join(current_dir, '../sample_images/R62_0323.CR3')


def test_RawImage_init():
    raw = RawImage(sample_image_path)
    assert isinstance(raw, RawImage)
    assert isinstance(raw.raw_image, np.ndarray)

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
