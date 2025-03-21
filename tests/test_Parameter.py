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

def test_Parameter_init_default():
    param = Parameter()

    assert isinstance(param, Parameter), "Object should be an instance of Parameter"
    assert param.exposure == 0, "Default exposure should be 0"
    assert param.contrast == 0, "Default contrast should be 0"
    assert param.highlights == 0, "Default highlights should be 0"
    assert param.shadows == 0, "Default shadows should be 0"
    assert param.black_levels == 0, "Default black_levels should be 0"
    assert param.saturation == 0, "Default saturation should be 0"


def test_Parameter_init_custom():
    param = Parameter(exposure=2, contrast=10, highlights=3, shadows=-2, black_levels=1, saturation=50)

    assert isinstance(param, Parameter), "Object should be an instance of Parameter"
    assert param.exposure == 2, "Custom exposure should be 2"
    assert param.contrast == 10, "Custom contrast should be 10"
    assert param.highlights == 3, "Custom highlights should be 3"
    assert param.shadows == -2, "Custom shadows should be -2"
    assert param.black_levels == 1, "Custom black_levels should be 1"
    assert param.saturation == 50, "Custom saturation should be 50"

