import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_keys():
    """Test if API keys are properly configured."""
    print("Checking API key configuration...")
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    horde_key = os.getenv("STABLE_HORDE_API_KEY")
    
    if gemini_key and gemini_key != "your_api_key_here":
        print(f"✓ Gemini API key configured (length: {len(gemini_key)})")
    else:
        print("✗ Gemini API key not configured")
    
    if horde_key and horde_key != "your_stable_horde_key_here":
        print(f"✓ Stable Horde API key configured (length: {len(horde_key)})")
    else:
        print("✗ Stable Horde API key not configured")
        print("  Note: Stable Horde works without API key but with lower priority")
    
    return bool(gemini_key) and bool(horde_key)

def test_horde_client():
    """Test the horde client functionality."""
    print("\nTesting Stable Horde client...")
    
    try:
        from horde_client import submit_horde_job, poll_horde_job
        
        # Submit a simple test job
        test_prompt = "A happy person, simple portrait"
        print(f"Submitting test job: '{test_prompt}'")
        
        job_id, response = submit_horde_job(test_prompt, params={"steps": 10, "width": 256, "height": 256})
        print(f"Job submitted successfully: {job_id}")
        
        return True
        
    except Exception as e:
        print(f"Horde client test failed: {e}")
        return False

def test_backend_imports():
    """Test if backend can import all required modules."""
    print("\nTesting backend imports...")
    
    try:
        from backend.main import app
        print("✓ Backend imports successful")
        return True
    except Exception as e:
        print(f"✗ Backend import failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Emotion Detection System Integration Test ===\n")
    
    # Test 1: API Keys
    keys_ok = test_api_keys()
    
    # Test 2: Backend Imports
    backend_ok = test_backend_imports()
    
    # Test 3: Horde Client (optional, requires network)
    print("\nWould you like to test Stable Horde connection? (y/n): ", end="")
    test_network = input().lower().startswith('y')
    
    horde_ok = True
    if test_network:
        horde_ok = test_horde_client()
    
    # Summary
    print(f"\n=== Test Results ===")
    print(f"API Keys: {'✓' if keys_ok else '✗'}")
    print(f"Backend: {'✓' if backend_ok else '✗'}")
    print(f"Horde: {'✓' if horde_ok else '✗'}")
    
    if keys_ok and backend_ok:
        print("\n✓ System ready! You can now:")
        print("1. Start backend: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
        print("2. Start frontend: python ui/app.py")
        print("3. Upload images and test emotion detection + generation!")
    else:
        print("\n✗ Please fix the issues above before running the system.")
        print("\nSetup steps:")
        print("1. Copy .env.example to .env")
        print("2. Add your GEMINI_API_KEY from https://aistudio.google.com/api-keys")
        print("3. Add your STABLE_HORDE_API_KEY from https://stablehorde.net/register")