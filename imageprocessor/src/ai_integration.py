import os
import json
from dotenv import load_dotenv

from PIL import Image
from google import genai
import httpx

from ImageProcessing import Parameter
from directory_management import generate_temp_dir


def _generate_prompt(prompt: str, parameters: Parameter) -> str:
    """Generate structured prompt for the API call."""
    return f"""
    Analyze this image: I want {prompt}; 
    Current parameters are {{exposure: {parameters.exposure}, contrast: {parameters.contrast}, 
    highlights: {parameters.highlights}, shadows: {parameters.shadows}, 
    black_levels: {parameters.black_levels}}} and return a JSON object with the following fields:
    {{
      "improvement_suggestions": "A couple of sentences on how to improve the image.",
      "exposure_adjustment": "A float number between -5 and 5 indicating the recommended stops of exposure adjustment.",
      "contrast_adjustment": "An integer between -100 and 100 indicating the recommended contrast adjustment.",
      "highlight_adjustment": "An integer between 0 and 100 indicating the recommended highlight adjustment.",
      "shadows_adjustment": "An integer between 0 and 100 indicating the recommended shadows adjustment.",
      "black_levels_adjustment": "An integer between 0 and 100 indicating the recommended black levels adjustment."
    }}
    Ensure the response is valid JSON and nothing else.
    """


class ImageAnalyzer:
    def __init__(self):
        """Initialize the ImageAnalyzer with API key and temp directory."""
        load_dotenv()
        self.temp_dir = generate_temp_dir()
        self.api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")

        if not self.api_key:
            raise ValueError("Missing GOOGLE_AI_STUDIO_API_KEY in environment variables")

        self.client = genai.Client(api_key=self.api_key)

    def _prepare_image(self, image_name='temp.tif') -> str:
        """Convert TIFF image to JPEG format for analysis."""
        tiff_path = os.path.join(self.temp_dir, image_name)
        jpeg_path = os.path.join(self.temp_dir, 'temp.jpeg')

        Image.open(tiff_path).save(jpeg_path)
        return jpeg_path

    def api_call(self, prompt: str, parameters: Parameter):
        """Make an API call with the given prompt and image parameters."""
        image_path = self._prepare_image()
        image = Image.open(image_path)

        structured_prompt = _generate_prompt(prompt, parameters)

        # Generate response
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[image, structured_prompt]
            )
        except httpx.ConnectError:
            return {
                'success': 0,
                'feedback': 'API call failed. No internet connection'
            }

        # Clean up the API response
        response_text = response.text.removeprefix('```json\n').removesuffix('\n```')

        try:
            response_json = json.loads(response_text)
        except json.decoder.JSONDecodeError:
            return {
                'success': 0,
                'feedback': 'API response is not valid JSON. Please try again.'
            }

        # Create a new Parameter object with updated values
        new_parameters = Parameter(
            exposure=response_json.get('exposure_adjustment', parameters.exposure),
            contrast=response_json.get('contrast_adjustment', parameters.contrast),
            highlights=response_json.get('highlight_adjustment', parameters.highlights),
            shadows=response_json.get('shadows_adjustment', parameters.shadows),
            black_levels=response_json.get('black_levels_adjustment', parameters.black_levels)
        )

        return {
            'success': 1,
            'feedback': response_json.get('improvement_suggestions', ''),
            'new_parameters': new_parameters
        }
