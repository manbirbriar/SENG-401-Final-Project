import os
import json
import pytest
from unittest.mock import MagicMock
from PIL import Image
import httpx
import sys
import httpx

sys.path.append('imageprocessor/src')

from ImageProcessing import Parameter
from ai_integration import ImageAnalyzer
from ImageProcessing import Parameter

def test_missing_api_key(monkeypatch):
    """Test that ImageAnalyzer raises an error when API key is missing."""
    
    # Override os.getenv to return None for the API key
    monkeypatch.setattr(os, "getenv", lambda key, default=None: None if key == "GOOGLE_AI_STUDIO_API_KEY" else default)
    
    # Expect ValueError due to missing API key
    with pytest.raises(ValueError, match="Missing GOOGLE_AI_STUDIO_API_KEY in environment variables"):
        ImageAnalyzer()


def test_prepare_image(tmpdir):
    """Test that _prepare_image correctly converts a TIFF to JPEG."""
    
    # Create a temporary directory
    temp_dir = str(tmpdir)
    
    # Mock the temp directory in ImageAnalyzer
    analyzer = ImageAnalyzer()
    analyzer.temp_dir = temp_dir  # Override default temp dir

    # Create a temporary TIFF image
    tiff_path = os.path.join(temp_dir, "temp.tif")
    image = Image.new("RGB", (100, 100), color="red")  # Create a red image
    image.save(tiff_path, format="TIFF")  # Save as TIFF

    # Call _prepare_image
    jpeg_path = analyzer._prepare_image()

    # Assertions
    assert os.path.exists(jpeg_path), "JPEG file was not created"
    assert jpeg_path.endswith(".jpeg"), "Output file is not a JPEG"

    # Verify the file is a valid JPEG
    with Image.open(jpeg_path) as img:
        assert img.format == "JPEG", "Output file is not a valid JPEG"

@pytest.fixture
def mock_analyzer(tmpdir, monkeypatch):
    """Fixture to provide a mock ImageAnalyzer with a temp directory."""
    analyzer = ImageAnalyzer()
    analyzer.temp_dir = str(tmpdir)  # Override temp directory
    
    # Mock the API client
    mock_client = MagicMock()
    analyzer.client = mock_client

    # Create a sample TIFF image to avoid file errors
    tiff_path = os.path.join(analyzer.temp_dir, "temp.tif")
    Image.new("RGB", (100, 100), color="blue").save(tiff_path, format="TIFF")

    return analyzer

def test_api_call(mock_analyzer):
    """Test a successful API call returns expected JSON response."""
    
    # Sample input parameters
    test_parameters = Parameter(
        exposure=0.0,
        contrast=10,
        highlights=20,
        shadows=30,
        black_levels=40
    )

    # Mock API response JSON
    mock_response_json = {
        "improvement_suggestions": "Increase contrast slightly.",
        "exposure_adjustment": 0.5,
        "contrast_adjustment": 15,
        "highlight_adjustment": 25,
        "shadows_adjustment": 35,
        "black_levels_adjustment": 45
    }

    # Mock the API response
    mock_analyzer.client.models.generate_content.return_value.text = json.dumps(mock_response_json)

    # Run the API call
    result = mock_analyzer.api_call("Enhance brightness", test_parameters)

    # Expected results
    assert result["success"] == 1, "API call should be successful"
    assert result["feedback"] == "Increase contrast slightly.", "Feedback mismatch"
    
    # Check updated parameters
    new_params = result["new_parameters"]
    assert new_params.exposure == 0.5
    assert new_params.contrast == 15
    assert new_params.highlights == 25
    assert new_params.shadows == 35
    assert new_params.black_levels == 45

@pytest.fixture
def mock_analyzer(monkeypatch):
    """Fixture to create a mock ImageAnalyzer with a mocked API client."""
    analyzer = ImageAnalyzer()

    # Mock the API client
    mock_client = MagicMock()
    analyzer.client = mock_client

    return analyzer

def test_api_call_no_internet(mock_analyzer):
    """Test API call handling when there is no internet connection."""
    
    # Sample input parameters
    test_parameters = Parameter(
        exposure=0.0,
        contrast=10,
        highlights=20,
        shadows=30,
        black_levels=40
    )

    # Simulate a network failure by raising httpx.ConnectError
    mock_analyzer.client.models.generate_content.side_effect = httpx.ConnectError("No internet connection")

    # Run the API call
    result = mock_analyzer.api_call("Enhance brightness", test_parameters)

    # Expected results
    assert result["success"] == 0, "API call should fail due to no internet"
    assert result["feedback"] == "API call failed. No internet connection", "Error message mismatch"

@pytest.fixture
def mock_analyzer(monkeypatch):
    """Fixture to create a mock ImageAnalyzer with a mocked API client."""
    analyzer = ImageAnalyzer()

    # Mock the API client
    mock_client = MagicMock()
    analyzer.client = mock_client

    return analyzer

def test_api_call_invalid_json(mock_analyzer):
    """Test API call handling when the response contains invalid JSON."""
    
    # Sample input parameters
    test_parameters = Parameter(
        exposure=0.0,
        contrast=10,
        highlights=20,
        shadows=30,
        black_levels=40
    )

    # Mock API response with invalid JSON
    mock_analyzer.client.models.generate_content.return_value.text = "{invalid_json_response: true,"

    # Run the API call
    result = mock_analyzer.api_call("Enhance brightness", test_parameters)

    # Expected results
    assert result["success"] == 0, "API call should fail due to invalid JSON"
    assert result["feedback"] == "API response is not valid JSON. Please try again.", "Error message mismatch"
