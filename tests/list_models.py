import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No API key found in .env file")
    exit(1)

# List available models
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print("Available models:")
    for model in data.get("models", []):
        name = model.get("name", "")
        display_name = model.get("displayName", "")
        methods = model.get("supportedGenerationMethods", [])
        
        if "generateContent" in methods:
            print(f"  {name} ({display_name}) - supports generateContent")
else:
    print(f"Error listing models: {response.status_code}")
    print(response.text)