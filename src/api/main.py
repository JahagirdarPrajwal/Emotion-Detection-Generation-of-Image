"""FastAPI backend for emotion detection and image generation."""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import base64
import os
import sys

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.clients.horde_client import submit_horde_job, poll_horde_job, b64_to_bytes
from src.clients.gemini_client import call_gemini_multimodal, DETECT_PROMPT

app = FastAPI(title="Emotion Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7860", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

EMOTION_PHRASES = {
    "happy": "gentle smile, eyes slightly crinkled, joyful expression",
    "sad": "downturned mouth, drooping eyes, melancholy expression", 
    "angry": "furrowed brow, intense gaze, stern expression",
    "surprised": "raised eyebrows, wide eyes, open mouth",
    "neutral": "calm expression, relaxed features, peaceful look",
    "disgust": "wrinkled nose, slight frown, disapproving look",
    "fear": "wide eyes, tense features, worried expression"
}


class EmotionResponse(BaseModel):
    dominant_emotion: str
    confidence: float
    all_scores: dict
    low_confidence: Optional[bool] = None


def validate_image_size(file: UploadFile) -> bytes:
    """Read and validate image file size."""
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 5MB limit")
    file.file.seek(0)
    return content


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "emotion-detection-api"}


@app.post("/api/detect-emotion", response_model=EmotionResponse)
async def detect_emotion(image: UploadFile = File(...)):
    """Detect emotion in uploaded image using Gemini API."""
    try:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        image_bytes = validate_image_size(image)
        result = call_gemini_multimodal(DETECT_PROMPT, image_bytes=image_bytes, mode="detect")
        
        required_keys = ["dominant_emotion", "confidence", "all_scores"]
        if not all(key in result for key in required_keys):
            raise HTTPException(status_code=500, detail="Invalid response from emotion detection service")
        
        return EmotionResponse(
            dominant_emotion=result["dominant_emotion"],
            confidence=result["confidence"],
            all_scores=result["all_scores"],
            low_confidence=result["confidence"] < 0.5
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")


@app.post("/api/edit-image")
async def edit_image(
    image: UploadFile = File(...),
    target_emotion: str = Form(...),
    intensity: float = Form(0.4)
):
    """Edit image to change facial expression using Stable Horde."""
    try:
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        if not 0.0 <= intensity <= 1.0:
            raise HTTPException(status_code=400, detail="Intensity must be between 0.0 and 1.0")
        
        if target_emotion.lower() not in EMOTION_PHRASES:
            raise HTTPException(status_code=400, detail=f"Unsupported emotion. Use: {list(EMOTION_PHRASES.keys())}")
        
        image_bytes = validate_image_size(image)
        img_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        emotion_phrase = EMOTION_PHRASES[target_emotion.lower()]
        prompt = f"same person, {emotion_phrase}, photorealistic portrait"
        
        denoising_strength = 0.2 + (intensity * 0.6)
        params = {
            "steps": 20,
            "width": 512,
            "height": 512,
            "denoising_strength": denoising_strength,
            "cfg_scale": 7.5,
            "sampler_name": "k_euler"
        }
        
        job_id, _ = submit_horde_job(prompt=prompt, model="stable_diffusion", init_image_b64=img_b64, params=params)
        images_b64, _ = poll_horde_job(job_id, timeout=300)
        
        if not images_b64:
            raise HTTPException(status_code=500, detail="No images generated")
        
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
    style: str = Form("photorealistic"),
    image: Optional[UploadFile] = File(None)
):
    """Generate image with specific emotion using Stable Horde."""
    try:
        if target_emotion.lower() not in EMOTION_PHRASES:
            raise HTTPException(status_code=400, detail=f"Unsupported emotion. Use: {list(EMOTION_PHRASES.keys())}")
        
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
        
        if image and image.filename:
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Seed file must be an image")
            
            image_bytes = validate_image_size(image)
            img_b64 = base64.b64encode(image_bytes).decode('utf-8')
            prompt = f"portrait of the same person, {emotion_phrase}, {style_desc}"
            params["denoising_strength"] = 0.6
        else:
            prompt = f"portrait of a person showing {emotion_phrase}, {style_desc}"
        
        job_id, _ = submit_horde_job(prompt=prompt, model="stable_diffusion", init_image_b64=img_b64, params=params)
        images_b64, _ = poll_horde_job(job_id, timeout=300)
        
        if not images_b64:
            raise HTTPException(status_code=500, detail="No images generated")
        
        result_bytes = b64_to_bytes(images_b64[0])
        
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