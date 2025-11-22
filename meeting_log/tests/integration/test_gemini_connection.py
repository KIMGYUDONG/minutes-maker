import google.generativeai as genai
import os
from dotenv import load_dotenv

def test_gemini_connection():
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-3-pro-preview")
    
    print(f"🔍 Testing Gemini Connection...")
    print(f"🔑 API Key found: {'Yes' if api_key else 'No'}")
    print(f"🤖 Model Name: {model_name}")
    
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env file.")
        return

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        print("📤 Sending test prompt: 'This is a test. Please summarize.'")
        response = model.generate_content("This is a test. Please summarize.")
        
        print("\n✅ Response Received:")
        print("-" * 50)
        print(response.text)
        print("-" * 50)
        print("🎉 Connection Successful!")
        
    except Exception as e:
        print(f"\n❌ Connection Failed: {str(e)}")
        print("\nTroubleshooting Tips:")
        print("1. Check if GEMINI_MODEL_NAME is correct (e.g., gemini-3-pro-preview)")
        print("2. Verify your API key has access to this model")
        print("3. Check your internet connection")

if __name__ == "__main__":
    test_gemini_connection()
