"""
Emotion Detection and Image Generation System
============================================

A web application that detects emotions in images and generates/modifies images with different emotions.

Quick Start:
1. Set up environment variables in .env file
2. Run the backend: python start_backend.py
3. Run the frontend: python start_frontend.py
4. Open http://localhost:7860 in your browser

Features:
- Emotion detection using Google Gemini API
- Image modification and generation using Stable Horde
- Web interface built with Gradio
- Support for multiple emotions and styles
"""

import os
import sys
import subprocess

def main():
    print(__doc__)
    
    choice = input("\nChoose an option:\n1. Start Backend API\n2. Start Frontend UI\n3. Start Both\nEnter choice (1-3): ")
    
    if choice == "1":
        print("Starting backend API (cleaned version of horde_handlers.py)...")
        os.system("uvicorn src.api.main:app --reload --port 8000")
    elif choice == "2":
        print("Starting frontend UI...")
        os.system("python src/ui/app.py")
    elif choice == "3":
        print("Starting both backend and frontend...")
        print("Backend will start first, then frontend in 3 seconds...")
        # Start backend in background
        subprocess.Popen([sys.executable, "-m", "uvicorn", "src.api.main:app", "--reload", "--port", "8000"])
        import time
        time.sleep(3)
        # Try different ports for frontend
        for port in [7860, 7861, 7862, 7863]:
            try:
                print(f"Trying to start frontend on port {port}...")
                os.system(f"python src/ui/app.py --server-port {port}")
                break
            except:
                continue
    else:
        print("Invalid choice. Exiting.")

if __name__ == "__main__":
    main()