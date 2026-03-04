# save as check_models.py in project root
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

for model in client.models.list():
    if "generatecontent" in [m.lower() for m in (model.supported_actions or [])]:
        print(model.name)