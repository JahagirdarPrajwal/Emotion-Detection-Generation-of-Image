import requests
import os

def test_fixed_endpoints():
    """Test the fixed backend endpoints."""
    BASE_URL = "http://localhost:8000"
    
    print("Testing Fixed Backend Endpoints")
    print("=" * 40)
    
    # Test health check
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✓ Main backend health check passed")
        else:
            print("✗ Main backend health check failed")
    except Exception as e:
        print(f"✗ Cannot connect to main backend: {e}")
        return
    
    # Test image modification with a test image
    if os.path.exists("sadface.jpg"):
        print("\nTesting image modification...")
        try:
            with open("sadface.jpg", "rb") as f:
                files = {"image": ("test.jpg", f, "image/jpeg")}
                data = {
                    "target_emotion": "happy",
                    "intensity": 0.5
                }
                response = requests.post(f"{BASE_URL}/api/edit-image", files=files, data=data)
                
                if response.status_code == 200:
                    print("✓ Image modification working")
                    print(f"  Response headers: {dict(response.headers)}")
                    print(f"  Content length: {len(response.content)} bytes")
                else:
                    print(f"✗ Image modification failed: {response.status_code}")
                    print(f"  Error: {response.text}")
                    
        except Exception as e:
            print(f"✗ Image modification error: {e}")
    else:
        print("⚠ No test image (sadface.jpg) found for testing")
    
    # Test image generation
    print("\nTesting image generation...")
    try:
        data = {
            "target_emotion": "happy",
            "style": "photorealistic"
        }
        response = requests.post(f"{BASE_URL}/api/generate-image", data=data)
        
        if response.status_code == 200:
            print("✓ Image generation working")
            print(f"  Content length: {len(response.content)} bytes")
        else:
            print(f"✗ Image generation failed: {response.status_code}")
            print(f"  Error: {response.text}")
            
    except Exception as e:
        print(f"✗ Image generation error: {e}")

def test_horde_handlers():
    """Test the new dedicated horde handlers."""
    HORDE_URL = "http://localhost:8001"  # Different port for horde handlers
    
    print("\n\nTesting Dedicated Horde Handlers")
    print("=" * 40)
    print("Note: Run with 'uvicorn backend.horde_handlers:app --port 8001' to test")
    
    try:
        response = requests.get(f"{HORDE_URL}/")
        if response.status_code == 200:
            print("✓ Horde handlers service is running")
            data = response.json()
            print(f"  Service: {data.get('service', 'unknown')}")
        else:
            print("✗ Horde handlers not accessible")
    except Exception as e:
        print(f"⚠ Horde handlers not running (expected): {e}")

if __name__ == "__main__":
    print("Backend Testing Script")
    print("Make sure the backend is running:")
    print("uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    print()
    
    test_fixed_endpoints()
    test_horde_handlers()
    
    print("\n" + "=" * 50)
    print("If main backend tests pass, the BytesIO error is fixed!")
    print("Your Gradio UI should now work properly.")
    print()
    print("Additional endpoints available:")
    print("• /api/edit-image-horde - Enhanced emotion editing")
    print("• /api/generate-image-horde - Enhanced image generation")