import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in .env file.")
    exit(1)

genai.configure(api_key=api_key)

print("🔍 Searching for Gemini models...")
print("-" * 50)

try:
    found_target = False
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            name = m.name
            display_name = m.display_name
            
            # Highlight Gemini 3 models
            if 'gemini-3' in name.lower() or 'gemini-3' in display_name.lower():
                print(f"✨ FOUND TARGET: {name} ({display_name})")
                found_target = True
            else:
                # Print others just in case, but maybe less prominent or just list them
                # User asked to print only models supporting generateContent, which we are doing.
                # User asked to filter and highlight. I'll print all but mark the target.
                print(f"  - {name} ({display_name})")

    if not found_target:
        print("-" * 50)
        print("⚠️ No 'gemini-3' models found. Please check if your API key has access or if the model is released.")

except Exception as e:
    print(f"❌ Error listing models: {str(e)}")
