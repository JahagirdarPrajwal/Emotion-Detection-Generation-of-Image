"""Gemini API client for emotion detection."""
import requests
import base64
import os
import time
import json
from typing import Dict, Optional, Union

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
DETECT_PROMPT = "Identify the dominant facial emotion in the attached image and return ONLY JSON: {dominant_emotion, confidence, all_scores}."


class GeminiAPIError(Exception):
    """Custom exception for Gemini API errors."""
    pass


def call_gemini_multimodal(prompt: str, image_bytes: Optional[bytes] = None, mode: str = "detect", extra_opts: Optional[Dict] = None) -> Union[Dict, bytes]:
    """Call Gemini multimodal API for emotion detection.
    
    Args:
        prompt: Text prompt to send
        image_bytes: Optional image data as bytes
        mode: Operation mode (currently only 'detect' is supported)
        extra_opts: Additional options to include in request
        
    Returns:
        Dict containing emotion analysis results
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiAPIError("GEMINI_API_KEY environment variable not set")
    
    headers = {"Content-Type": "application/json"}
    parts = [{"text": prompt}]
    
    if image_bytes:
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image_b64
            }
        })
    
    payload = {"contents": [{"parts": parts}]}
    if extra_opts:
        payload.update(extra_opts)
    
    url = f"{GEMINI_ENDPOINT}?key={api_key}"
    
    for attempt in range(2):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return _handle_response(response, mode)
            
            if response.status_code >= 500 and attempt == 0:
                time.sleep(1)
                continue
                
            raise GeminiAPIError(f"API request failed: {response.status_code} - {response.text}")
            
        except requests.exceptions.RequestException as e:
            if attempt == 0:
                time.sleep(1)
                continue
            raise GeminiAPIError(f"Network error: {e}")
    
    raise GeminiAPIError("Max retries exceeded")


def _handle_response(response: requests.Response, mode: str) -> Union[Dict, bytes]:
    """Process API response for emotion detection."""
    try:
        data = response.json()
        
        if "candidates" in data and len(data["candidates"]) > 0:
            candidate = data["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                text_content = candidate["content"]["parts"][0].get("text", "")
                
                if mode == "detect":
                    clean_text = text_content.strip()
                    if clean_text.startswith("```json"):
                        clean_text = clean_text[7:]
                    if clean_text.endswith("```"):
                        clean_text = clean_text[:-3]
                    clean_text = clean_text.strip()
                    
                    try:
                        emotion_data = json.loads(clean_text)
                        required_keys = ["dominant_emotion", "confidence", "all_scores"]
                        if not all(key in emotion_data for key in required_keys):
                            raise GeminiAPIError(f"Invalid detect response: missing required keys {required_keys}")
                        return emotion_data
                    except json.JSONDecodeError:
                        raise GeminiAPIError(f"Could not parse JSON from response: {clean_text[:200]}...")
        
        raise GeminiAPIError("Invalid response format from Gemini API")
        
    except ValueError:
        raise GeminiAPIError("Invalid JSON response")