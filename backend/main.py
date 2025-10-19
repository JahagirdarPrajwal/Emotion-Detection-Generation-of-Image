# DEPRECATED: This file is deprecated. Use src/api/main.py instead.
# For new installations, run: uvicorn src.api.main:app --reload --port 8000

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

# Import our custom clients
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.clients.gemini_client import call_gemini_multimodal, DETECT_PROMPT
from src.clients.horde_client import submit_horde_job, poll_horde_job, b64_to_bytes

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
    # Reset file pointer for subsequent reads
    file.file.seek(0)
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
        
        # Convert image to base64 for Stable Horde
        init_image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Map intensity to denoising strength
        denoising_strength = 0.3 + (intensity * 0.4)  # 0.3 to 0.7 range
        
        # Create prompt for emotion modification
        prompt = f"Change the facial expression to show {target_emotion} emotion, keep the same person, background, and pose, photorealistic, high quality"
        
        # Parameters for image-to-image generation
        params = {
            "denoising_strength": denoising_strength,
            "steps": 25,
            "width": 512,
            "height": 512,
            "cfg_scale": 7.5
        }
        
        # Submit job to Stable Horde
        job_id, _ = submit_horde_job(
            prompt=prompt,
            model="stable_diffusion",
            init_image_b64=init_image_b64,
            params=params
        )
        
        # Poll for completion
        images_b64, _ = poll_horde_job(job_id, timeout=300)
        
        # Convert first image back to bytes
        result_bytes = b64_to_bytes(images_b64[0])
        
        return Response(
            content=result_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=edited_image.png"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error editing image: {str(e)}")

@app.post("/api/generate-image")
async def generate_image(
    target_emotion: str = Form(...),
    style: str = Form(default="photorealistic"),
    image: Optional[UploadFile] = File(None)
):
    """Generate new image with specified emotion."""
    try:
        init_image_b64 = None
        seed_used = False
        
        if image:
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            image_bytes = validate_file_size(image)
            init_image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            seed_used = True
        
        # Create generation prompt based on style and emotion
        style_prompts = {
            "photorealistic": "photorealistic, high quality, detailed",
            "cartoon": "cartoon style, animated, colorful",
            "oil": "oil painting style, artistic, painterly"
        }
        
        style_desc = style_prompts.get(style, "photorealistic, high quality")
        
        if seed_used:
            prompt = f"A person showing {target_emotion} emotion, {style_desc}, preserve facial features and general appearance"
            params = {
                "denoising_strength": 0.6,
                "steps": 30,
                "width": 512,
                "height": 512,
                "cfg_scale": 7.5
            }
        else:
            prompt = f"Portrait of a person with {target_emotion} facial expression, {style_desc}, clear face, good lighting"
            params = {
                "steps": 30,
                "width": 512,
                "height": 512,
                "cfg_scale": 7.5
            }
        
        # Submit job to Stable Horde
        job_id, _ = submit_horde_job(
            prompt=prompt,
            model="stable_diffusion",
            init_image_b64=init_image_b64,
            params=params
        )
        
        # Poll for completion
        images_b64, _ = poll_horde_job(job_id, timeout=300)
        
        # Convert first image back to bytes
        result_bytes = b64_to_bytes(images_b64[0])
        
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
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)