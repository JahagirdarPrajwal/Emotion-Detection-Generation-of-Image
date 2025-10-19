import requests
import base64
import os
import time
import json
from typing import Dict, Optional, Union

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, will use system env vars
    pass

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

DETECT_PROMPT = "Identify the dominant facial emotion in the attached image and return ONLY JSON: {dominant_emotion, confidence, all_scores}."

EDIT_PROMPT_TEMPLATE = "Edit the provided image to change ONLY the facial expression to TARGET_EMOTION while preserving identity, pose, background, hair and clothing. Intensity: INTENSITY. Use photorealistic editing and return image bytes and metadata JSON."

GENERATE_PROMPT_TEMPLATE = "Generate a new image reflecting TARGET_EMOTION. If seed image provided, preserve identity and approximate pose; otherwise produce a new portrait. Style: STYLE. Return image bytes and metadata JSON."


class GeminiAPIError(Exception):
    pass


def call_gemini_multimodal(prompt: str, image_bytes: Optional[bytes] = None, mode: str = "detect", extra_opts: Optional[Dict] = None) -> Union[Dict, bytes]:
    """Call Gemini multimodal API for emotion detection, editing, or generation.
    
    Args:
        prompt: Text prompt to send
        image_bytes: Optional image data as bytes
        mode: Operation mode - 'detect', 'edit', or 'generate'
        extra_opts: Additional options to include in request
        
    Returns:
        Dict for detect mode, bytes for edit/generate modes
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiAPIError("GEMINI_API_KEY environment variable not set")
    
    headers = {"Content-Type": "application/json"}
    
    # Build request payload for Gemini API
    parts = [{"text": prompt}]
    
    if image_bytes:
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image_b64
            }
        })
        print(f"Sending {mode} request with image ({len(image_bytes)} bytes)")
    else:
        print(f"Sending {mode} request without image")
    
    payload = {
        "contents": [{"parts": parts}]
    }
    
    if extra_opts:
        payload.update(extra_opts)
    
    url = f"{GEMINI_ENDPOINT}?key={api_key}"
    
    for attempt in range(2):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return _handle_response(response, mode)
            
            if response.status_code >= 500 and attempt == 0:
                print(f"Server error {response.status_code}, retrying...")
                time.sleep(1)
                continue
                
            raise GeminiAPIError(f"API request failed: {response.status_code} - {response.text}")
            
        except requests.exceptions.RequestException as e:
            if attempt == 0:
                print(f"Request failed, retrying: {e}")
                time.sleep(1)
                continue
            raise GeminiAPIError(f"Network error: {e}")
    
    raise GeminiAPIError("Max retries exceeded")


def _handle_response(response: requests.Response, mode: str) -> Union[Dict, bytes]:
    """Process API response based on mode."""
    try:
        data = response.json()
        
        # Extract text from Gemini response format
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                text_content = candidate["content"]["parts"][0].get("text", "")
                
                if mode == "detect":
                    # Clean up markdown formatting that Gemini might add
                    clean_text = text_content.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:]  # Remove ```json
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]  # Remove ```
                    clean_text = clean_text.strip()
                    
                    # Try to parse JSON from the cleaned response
                    try:
                        emotion_data = json.loads(clean_text)
                        required_keys = ["dominant_emotion", "confidence", "all_scores"]
                        if not all(key in emotion_data for key in required_keys):
                            raise GeminiAPIError(f"Invalid detect response: missing required keys {required_keys}")
                        return emotion_data
                    except json.JSONDecodeError:
                        # Fallback: return raw response for debugging
                        raise GeminiAPIError(f"Could not parse JSON from response: {clean_text[:200]}...")
                
                elif mode in ("edit", "generate"):
                    # For image generation, Gemini API doesn't directly return images
                    # This would need integration with an image generation service
                    # For now, return placeholder
                    raise GeminiAPIError(f"Image {mode} not implemented - requires additional image generation service")
        
        raise GeminiAPIError("Invalid response format from Gemini API")
        
    except ValueError:
        raise GeminiAPIError("Invalid JSON response")


def build_edit_prompt(target_emotion: str, intensity: str = "moderate") -> str:
    """Build edit prompt with target emotion and intensity."""
    return EDIT_PROMPT_TEMPLATE.replace("TARGET_EMOTION", target_emotion).replace("INTENSITY", intensity)


def build_generate_prompt(target_emotion: str, style: str = "photorealistic") -> str:
    """Build generate prompt with target emotion and style."""
    return GENERATE_PROMPT_TEMPLATE.replace("TARGET_EMOTION", target_emotion).replace("STYLE", style)


if __name__ == "__main__":
    # Example usage
    try:
        # Set up a test environment variable (for demo only)
        if not os.getenv("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = "demo_key_12345"
        
        # Test with a small sample image (1x1 pixel JPEG)
        sample_image = base64.b64decode(
            "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB"
            "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEB"
            "AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB"
            "/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAA"
            "AAAAAAAAAAAAAAAK/8QAFBEBAAAAAAAAAAAAAAAAAAAAA//aAAwDAQACEQMRAD8A0/WAK/9k="
        )
        
        print("Testing emotion detection...")
        result = call_gemini_multimodal(DETECT_PROMPT, sample_image, "detect")
        print(f"Detection result: {result}")
        
    except Exception as e:
        print(f"Demo failed (expected for placeholder endpoint): {e}")