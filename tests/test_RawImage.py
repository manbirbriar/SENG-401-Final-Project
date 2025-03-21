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