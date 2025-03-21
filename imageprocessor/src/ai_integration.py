import os
import json
from dotenv import load_dotenv

from PIL import Image
from google import genai
import httpx

from ImageProcessing import Parameter
from directory_management import generate_temp_dir


TEMP_DIR = generate_temp_dir()
load_dotenv()
GOOGLE_AI_STUDIO_API_KEY = os.getenv("GOOGLE_AI_STUDIO_API_KEY")

client = genai.Client(api_key=GOOGLE_AI_STUDIO_API_KEY)

def api_call(prompt: str, current_parameters: Parameter):
    # Placeholder for API call
    # Define a structured prompt
    prompt = f"""Analyze this image: I want {prompt}; Current parameters are {{exposure: {current_parameters.exposure}, contrast: {current_parameters.contrast}, highlights: {current_parameters.highlights}, shadows: {current_parameters.shadows}, black_levels: {current_parameters.black_levels}}} and return a JSON object with the following fields:
    {{
      "improvement_suggestions": "A couple of sentences on how to improve the image.",
      "exposure_adjustment": "An float number between -5 and 5 indicating the recommended stops of exposure adjustment.",
      "contrast_adjustment": "An integer between -100 and 100 indicating the recommended contrast adjustment.",
      "highlight_adjustment": "An integer between 0 and 100 indicating the recommended highlight adjustment.",
      "shadows_adjustment": "An integer between 0 and 100 indicating the recommended shadows adjustment.",
      "black_levels_adjustment": "An integer between 0 and 100 indicating the recommended black levels adjustment."
    }}
    Ensure the response is valid JSON and nothing else.
    """
    Image.open(os.path.join(TEMP_DIR, 'temp.tif')).save(os.path.join(TEMP_DIR, 'temp.jpeg'))
    image = Image.open(os.path.join(TEMP_DIR, 'temp.jpeg'))
    # Generate structured response
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[image, prompt]
        )
    except httpx.ConnectError:
        return {
            'success': 0,
            'feedback': 'API call failed. No internet connection'
        }
    response = response.text.removeprefix('```json\n').removesuffix('\n```')
    try:
        response = json.loads(response)
    except json.decoder.JSONDecodeError:
        return {
            'success': 0,
            'feedback': 'API response is not valid JSON. Please try again.'
        }
    parameter = Parameter(
        exposure=response['exposure_adjustment'],
        contrast=response['contrast_adjustment'],
        highlights=response['highlight_adjustment'],
        shadows=response['shadows_adjustment'],
        black_levels=response['black_levels_adjustment']
    )
    return {
        'success': 1,
        'feedback': response['improvement_suggestions'],
        'new_parameters': parameter
    }
