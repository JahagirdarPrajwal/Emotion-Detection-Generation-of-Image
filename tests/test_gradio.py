import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing Gradio app import...")
    from ui.app import app
    print("Successfully imported Gradio app")
    print("App created successfully")
    
    print("\nTo run the app:")
    print("1. Make sure FastAPI backend is running: uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
    print("2. Install dependencies: pip install gradio pillow requests")
    print("3. Run the UI: python ui/app.py")
    print("4. Open browser to: http://localhost:7860")
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required dependencies:")
    print("pip install gradio pillow requests")
except Exception as e:
    print(f"Error: {e}")