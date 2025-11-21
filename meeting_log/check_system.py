"""Quick verification script to check system requirements."""

import sys


def check_python_version():
    """Check Python version."""
    print("🐍 Python Version Check")
    version = sys.version_info
    print(f"   Version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("   ❌ Python 3.10 or higher is required")
        return False
    else:
        print("   ✅ Python version OK")
        return True


def check_cuda():
    """Check CUDA availability."""
    print("\n🎮 GPU/CUDA Check")
    try:
        import torch
        print(f"   PyTorch: {torch.__version__}")
        
        if torch.cuda.is_available():
            print(f"   ✅ CUDA available: {torch.version.cuda}")
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
            props = torch.cuda.get_device_properties(0)
            vram_gb = props.total_memory / (1024**3)
            print(f"   VRAM: {vram_gb:.1f} GB")
            return True
        else:
            print("   ⚠️ CUDA not available - will run on CPU (slower)")
            return False
    except ImportError:
        print("   ❌ PyTorch not installed")
        return False


def check_dependencies():
    """Check if all required packages are installed."""
    print("\n📦 Dependency Check")
    
    required_packages = [
        ('streamlit', 'Streamlit'),
        ('whisper', 'OpenAI Whisper'),
        ('google.generativeai', 'Google Generative AI'),
        ('notion_client', 'Notion Client'),
        ('dotenv', 'Python Dotenv'),
        ('pydub', 'Pydub'),
        ('torchaudio', 'TorchAudio'),
    ]
    
    all_ok = True
    for module_name, display_name in required_packages:
        try:
            __import__(module_name)
            print(f"   ✅ {display_name}")
        except ImportError:
            print(f"   ❌ {display_name} - not installed")
            all_ok = False
    
    return all_ok


def check_env_file():
    """Check if .env file exists and has required variables."""
    print("\n🔐 Configuration Check")
    
    try:
        from pathlib import Path
        env_path = Path(__file__).parent / '.env'
        
        if not env_path.exists():
            print("   ❌ .env file not found")
            print("   Please copy .env.example to .env and fill in your API keys")
            return False
        
        print("   ✅ .env file exists")
        
        # Check if variables are set
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        required_vars = ['GEMINI_API_KEY', 'NOTION_TOKEN', 'NOTION_PAGE_ID']
        missing = []
        
        for var in required_vars:
            value = os.getenv(var, '')
            if not value or 'your_' in value.lower():
                missing.append(var)
        
        if missing:
            print(f"   ⚠️ Missing or incomplete variables: {', '.join(missing)}")
            return False
        else:
            print("   ✅ All API keys configured")
            return True
            
    except Exception as e:
        print(f"   ❌ Error checking configuration: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 50)
    print("Meeting Minutes Service - System Check")
    print("=" * 50)
    
    results = []
    results.append(check_python_version())
    results.append(check_cuda())
    results.append(check_dependencies())
    results.append(check_env_file())
    
    print("\n" + "=" * 50)
    if all(results):
        print("🎉 All checks passed! You're ready to go.")
        print("\nTo start the service, run:")
        print("   streamlit run app.py --server.address=0.0.0.0")
    else:
        print("⚠️ Some checks failed. Please address the issues above.")
        print("\nTo install dependencies, run:")
        print("   pip install -r requirements.txt")
    print("=" * 50)


if __name__ == "__main__":
    main()
