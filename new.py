from google import genai

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
        "Describe the photo",
    ],
)
print(f"{result.text=}")