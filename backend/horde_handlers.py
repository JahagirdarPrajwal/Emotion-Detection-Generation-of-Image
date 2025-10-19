# DEPRECATED: This file is deprecated. Use src/api/main.py instead.
# For new installations, run: uvicorn src.api.main:app --reload --port 8000

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional
import io
import base64
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.clients.horde_client import submit_horde_job, poll_horde_job, b64_to_bytes
from src.clients.gemini_client import call_gemini_multimodal, DETECT_PROMPT

app = FastAPI(title="Horde Image API", version="1.0.0")

# CORS middleware for Gradio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7860", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Emotion mapping for better prompts
EMOTION_PHRASES = {
    "happy": "gentle smile, eyes slightly crinkled, joyful expression",
    "sad": "downturned mouth, drooping eyes, melancholy expression", 
    "angry": "furrowed brow, intense gaze, stern expression",
    "surprised": "raised eyebrows, wide eyes, open mouth",
    "neutral": "calm expression, relaxed features, peaceful look",
    "disgust": "wrinkled nose, slight frown, disapproving look",
    "fear": "wide eyes, tense features, worried expression"
}

class ErrorResponse(BaseModel):
    error: str

class EmotionResponse(BaseModel):
    dominant_emotion: str
    confidence: float
    all_scores: dict
    low_confidence: Optional[bool] = None

def validate_image_size(file: UploadFile) -> bytes:
    """Read and validate image file size."""
    # Read the content
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 5MB limit")
    # Reset the file pointer for any subsequent reads
    file.file.seek(0)
    # Return the content directly
    return content

@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "horde-handlers"}

@app.post("/api/detect-emotion", response_model=EmotionResponse)
async def detect_emotion(image: UploadFile = File(...)):
    """Detect emotion in uploaded image using Gemini API."""
    try:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        image_bytes = validate_image_size(image)
        
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

@app.post("/api/edit-image-horde")
async def edit_image_horde(
    image: UploadFile = File(...),
    target_emotion: str = Form(...),
    intensity: float = Form(0.4)
):
    """Edit image using Stable Horde img2img to change facial expression."""
    try:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        if not 0.0 <= intensity <= 1.0:
            raise HTTPException(status_code=400, detail="Intensity must be between 0.0 and 1.0")
        
        if target_emotion.lower() not in EMOTION_PHRASES:
            raise HTTPException(status_code=400, detail=f"Unsupported emotion. Use: {list(EMOTION_PHRASES.keys())}")
        
        # Read and validate image
        image_bytes = validate_image_size(image)
        
        # Convert to base64 (no data: prefix)
        img_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Build emotion-specific prompt
        emotion_phrase = EMOTION_PHRASES[target_emotion.lower()]
        prompt = f"same person, {emotion_phrase}, photorealistic portrait"
        
        # Map intensity to denoising strength
        denoising_strength = 0.2 + (intensity * 0.6)  # Range: 0.2 to 0.8
        
        # Parameters for img2img
        params = {
            "steps": 20,
            "width": 512,
            "height": 512,
            "denoising_strength": denoising_strength,
            "cfg_scale": 7.5,
            "sampler_name": "k_euler"
        }
        
        # Submit job to Stable Horde
        print(f"Submitting to Stable Horde with prompt: {prompt}")
        job_id, submit_response = submit_horde_job(
            prompt=prompt,
            model="stable_diffusion",
            init_image_b64=img_b64,
            params=params
        )
        print(f"Job submitted: {job_id}")
        
        # Poll for completion
        print("Polling for completion...")
        images_b64, final_response = poll_horde_job(job_id, timeout=300)
        print(f"Got {len(images_b64) if images_b64 else 0} images")
        
        if not images_b64:
            raise HTTPException(status_code=500, detail="No images generated")
        
        # Convert first image to bytes
        print(f"Raw base64 length: {len(images_b64[0])}")
        print(f"Base64 starts with: {images_b64[0][:100]}")
        result_bytes = b64_to_bytes(images_b64[0])
        print(f"Result image size: {len(result_bytes)} bytes")
        print(f"Image bytes start with: {result_bytes[:20].hex()}")
        
        # Return as Response with proper content type
        return Response(
            content=result_bytes,
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=edited_image.png"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error editing image: {str(e)}")

@app.post("/api/edit-image")
async def edit_image(
    image: UploadFile = File(...),
    target_emotion: str = Form(...),
    intensity: float = Form(...)
):
    """Standard edit image endpoint (same as edit-image-horde)."""
    return await edit_image_horde(image, target_emotion, intensity)

@app.post("/api/generate-image")
async def generate_image(
    target_emotion: str = Form(...),
    style: str = Form("photorealistic"),
    image: Optional[UploadFile] = File(None)
):
    """Standard generate image endpoint (same as generate-image-horde)."""
    return await generate_image_horde(target_emotion, style, image)

@app.post("/api/generate-image-horde")
async def generate_image_horde(
    target_emotion: str = Form(...),
    style: str = Form("photorealistic"),
    image: Optional[UploadFile] = File(None)
):
    """Generate image using Stable Horde with optional seed image."""
    try:
        if target_emotion.lower() not in EMOTION_PHRASES:
            raise HTTPException(status_code=400, detail=f"Unsupported emotion. Use: {list(EMOTION_PHRASES.keys())}")
        
        # Style mapping
        style_phrases = {
            "photorealistic": "photorealistic, high detail, professional photography",
            "cartoon": "cartoon style, animated, colorful, digital art",
            "oil": "oil painting style, artistic, painterly, classical art"
        }
        
        style_desc = style_phrases.get(style.lower(), "photorealistic, high detail")
        emotion_phrase = EMOTION_PHRASES[target_emotion.lower()]
        
        img_b64 = None
        params = {
            "steps": 25,
            "width": 512,
            "height": 512,
            "cfg_scale": 7.5,
            "sampler_name": "k_euler"
        }
        
        # Check if seed image provided
        if image and image.filename:
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Seed file must be an image")
            
            # Read and encode seed image
            image_bytes = validate_image_size(image)
            img_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Img2img prompt (preserve identity)
            prompt = f"portrait of the same person, {emotion_phrase}, {style_desc}"
            params["denoising_strength"] = 0.6
            
        else:
            # Text2img prompt (new person)
            prompt = f"portrait of a person showing {emotion_phrase}, {style_desc}"
        
        # Submit job to Stable Horde
        job_id, submit_response = submit_horde_job(
            prompt=prompt,
            model="stable_diffusion",
            init_image_b64=img_b64,
            params=params
        )
        
        # Poll for completion
        images_b64, final_response = poll_horde_job(job_id, timeout=300)
        
        if not images_b64:
            raise HTTPException(status_code=500, detail="No images generated")
        
        # Convert first image to bytes
        result_bytes = b64_to_bytes(images_b64[0])
        
        # Return as Response with proper content type
        return Response(
            content=result_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": "attachment; filename=generated_image.png",
                "X-Style": style,
                "X-Target-Emotion": target_emotion,
                "X-Seed-Used": str(bool(img_b64))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)