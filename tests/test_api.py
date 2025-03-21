import os
import sys
import pytest
import json
from PIL import Image
from dotenv import load_dotenv

sys.path.append('imageprocessor/src')

from ImageProcessing import Parameter
from directory_management import generate_temp_dir
from ai_integration import api_call 

temp_dir = generate_temp_dir()
load_dotenv()

@pytest.fixture
def sample_image():
    """Creates a temporary image for testing"""
    image_path = os.path.join(temp_dir, 'temp.tif')
    img = Image.new('RGB', (100, 100), color='white')
    img.save(image_path)
    return image_path

@pytest.fixture
def sample_parameters():
    """Returns a sample Parameter object"""
    return Parameter(exposure=0.0, contrast=0, highlights=0)

def test_api_call(sample_image, sample_parameters):
    prompt = "enhance brightness and contrast"
    result = api_call(prompt, sample_parameters)
    
    assert isinstance(result, dict)
    assert 'success' in result and result['success'] == 1
    assert 'feedback' in result and isinstance(result['feedback'], str)
    assert 'new_parameters' in result and isinstance(result['new_parameters'], Parameter)
    
    assert -5.0 <= result['new_parameters'].exposure <= 5.0
    assert -100 <= result['new_parameters'].contrast <= 100
    assert -100 <= result['new_parameters'].highlights <= 100

# once pushed test failed api test
