# Goal: Get Gemini to just work
# Resource: https://ai.google.dev/gemini-api/docs/quickstart#python
# Resource 2: https://ai.google.dev/gemini-api/docs/api-key#set-api-env-var

from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

API_key = os.getenv('GEMINI_API_KEY')

client = genai.Client()
response = client.models.generate_content(
    model='gemini-3-flash-preview', contents='Explain how AI works in a few words'
)

print(response.text)
