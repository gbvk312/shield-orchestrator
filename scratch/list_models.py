import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

print("Listing supported models for your API key...")
try:
    models = client.models.list()
    for m in models:
        print(f" - {m.id}")
except Exception as e:
    print(f"Error listing models: {e}")
