from google import genai
import json

# Initialize the GenAI client
client = genai.Client(api_key="AIzaSyAFZWyoJrn8P62z5Hb6uhrPKeCYLmCfUgs")

# Provide the correct file path to the image
file_path = "phone.png"  # Replace with the actual path to your image

# Upload the image file
myfile = client.files.upload(file=file_path)
print(f"{myfile=}")

# Generate content using the uploaded file
result = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[
        myfile,
        "\n\n",
        "Given the photo, recommend changes for three sliders: contrast, saturation, and brightness (each with 10 levels). "
        "Respond in JSON format with keys: 'contrast', 'saturation', and 'brightness', each having an integer value from 1 to 10. And key 'resp' with a string with reasoning for the values",
    ],
)

print(result.text)
