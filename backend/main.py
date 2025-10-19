# uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from pydantic import BaseModel
from typing import Optional, Dict, Any
import io
import base64
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our custom gemini client
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gemini_client import call_gemini_multimodal, DETECT_PROMPT, build_edit_prompt, build_generate_prompt

app = FastAPI(title="Emotion Detection API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7860", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB

class EmotionResponse(BaseModel):
    dominant_emotion: str
    confidence: float
    all_scores: Dict[str, float]
    low_confidence: Optional[bool] = None

class ErrorResponse(BaseModel):
    error: str

def validate_file_size(file: UploadFile) -> bytes:
    """Read and validate file size."""
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 3MB limit")
    return content

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

@app.post("/api/detect-emotion", response_model=EmotionResponse)
async def detect_emotion(image: UploadFile = File(...)):
    """Detect emotion in uploaded image."""
    try:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        image_bytes = validate_file_size(image)
        
        result = call_gemini_multimodal(DETECT_PROMPT, image_bytes=image_bytes, mode="detect")
        
        # Validate response format
        required_keys = ["dominant_emotion", "confidence", "all_scores"]
        if not all(key in result for key in required_keys):
            raise HTTPException(status_code=500, detail="Invalid response from emotion detection service")
        
        # Check for low confidence
        low_confidence = result["confidence"] < 0.5
        
        return EmotionResponse(
            dominant_emotion=result["dominant_emotion"],
            confidence=result["confidence"],
            all_scores=result["all_scores"],
            low_confidence=low_confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@app.post("/api/edit-image")
async def edit_image(
    image: UploadFile = File(...),
    target_emotion: str = Form(...),
    intensity: float = Form(...)
):
    """Edit image to change facial expression to target emotion."""
    try:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        if not 0.0 <= intensity <= 1.0:
            raise HTTPException(status_code=400, detail="Intensity must be between 0.0 and 1.0")
        
        image_bytes = validate_file_size(image)
        
        # Map intensity to descriptive terms
        intensity_map = {
            (0.0, 0.3): "subtle",
            (0.3, 0.7): "moderate", 
            (0.7, 1.0): "strong"
        }
        
        intensity_desc = "moderate"
        for (min_val, max_val), desc in intensity_map.items():
            if min_val <= intensity <= max_val:
                intensity_desc = desc
                break
        
        prompt = build_edit_prompt(target_emotion, intensity_desc)
        
        result_bytes = call_gemini_multimodal(
            prompt, 
            image_bytes=image_bytes, 
            mode="edit",
            extra_opts={"intensity": intensity}
        )
        
        return Response(
            content=result_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=edited_image.png"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # For now, return error since edit mode isn't fully implemented in gemini_client
        raise HTTPException(status_code=501, detail="Image editing not yet implemented")

@app.post("/api/generate-image")
async def generate_image(
    target_emotion: str = Form(...),
    style: str = Form(default="photorealistic"),
    image: Optional[UploadFile] = File(None)
):
    """Generate new image with specified emotion."""
    try:
        image_bytes = None
        seed_used = False
        
        if image:
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            image_bytes = validate_file_size(image)
            seed_used = True
        
        prompt = build_generate_prompt(target_emotion, style)
        
        result_bytes = call_gemini_multimodal(
            prompt,
            image_bytes=image_bytes,
            mode="generate",
            extra_opts={"style": style, "seed_used": seed_used}
        )
        
        return Response(
            content=result_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": "attachment; filename=generated_image.png",
                "X-Seed-Used": str(seed_used),
                "X-Style": style,
                "X-Target-Emotion": target_emotion
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # For now, return error since generate mode isn't fully implemented in gemini_client
        raise HTTPException(status_code=501, detail="Image generation not yet implemented")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)