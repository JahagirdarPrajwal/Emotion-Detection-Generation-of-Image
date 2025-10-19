import requests
import os

# Test the FastAPI backend endpoints
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Health check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_detect_emotion():
    """Test emotion detection endpoint."""
    try:
        # Use the same test image from before
        with open("sadface.jpg", "rb") as f:
            files = {"image": ("sadface.jpg", f, "image/jpeg")}
            response = requests.post(f"{BASE_URL}/api/detect-emotion", files=files)
            print(f"Emotion detection: {response.status_code}")
            if response.status_code == 200:
                print(f"Result: {response.json()}")
            else:
                print(f"Error: {response.text}")
            return response.status_code == 200
    except Exception as e:
        print(f"Emotion detection test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing FastAPI backend...")
    print("Make sure to start the server first with:")
    print("uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    print()
    
    if test_health():
        print("✓ Health check passed")
    else:
        print("✗ Health check failed")
    
    if test_detect_emotion():
        print("✓ Emotion detection passed")
    else:
        print("✗ Emotion detection failed")