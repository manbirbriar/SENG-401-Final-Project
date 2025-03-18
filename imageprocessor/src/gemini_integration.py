from PIL import Image
from google import genai
import json
from dotenv import load_dotenv
import os
load_dotenv() 

getapikey = os.getenv("MY_API_KEY")

client = genai.Client(api_key = getapikey)

# Load the image
image = Image.open("phone.png")

# Define a structured prompt
prompt = """Analyze this image and return a JSON object with the following fields:
{
  "description": "A one-sentence description of the image.",
  "improvement_suggestions": "A couple of sentences on how to improve the image.",
  "contrast_adjustment": "An integer between 0 and 100 indicating the recommended contrast adjustment.",
  "highlight_adjustment": "An integer between 0 and 100 indicating the recommended highlight adjustment.",
  "exposure_adjustment": "An integer between 0 and 100 indicating the recommended exposure adjustment."
}
Ensure the response is valid JSON and nothing else.
"""

# Generate structured response
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[image, prompt]
)

print(response.text)
