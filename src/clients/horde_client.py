"""Stable Horde API client for image generation."""
import requests
import time
import base64
import logging
import os
from typing import Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUBMIT_ENDPOINT = "https://stablehorde.net/api/v2/generate/async"
STATUS_ENDPOINT = "https://stablehorde.net/api/v2/generate/status/{}"


def submit_horde_job(prompt: str, model: str = "stable_diffusion", init_image_b64: Optional[str] = None, 
                     params: Optional[Dict] = None) -> Tuple[str, Dict]:
    """Submit an image generation job to AI Horde."""
    default_params = {
        "steps": 30,
        "width": 512,
        "height": 512,
        "cfg_scale": 7.5,
        "sampler_name": "k_euler"
    }
    
    if params:
        default_params.update(params)
    
    payload = {
        "prompt": prompt,
        "models": [model],
        "params": default_params,
        "nsfw": False,
        "trusted_workers": True,
        "r2": True
    }
    
    if init_image_b64:
        payload["source_image"] = init_image_b64
        if "denoising_strength" not in default_params:
            payload["params"]["denoising_strength"] = 0.75
    
    api_key = os.getenv("STABLE_HORDE_API_KEY", "0000000000")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "EmotionDetectionApp/1.0",
        "apikey": api_key
    }
    
    for attempt in range(2):
        try:
            response = requests.post(SUBMIT_ENDPOINT, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 202:
                data = response.json()
                job_id = data.get("id")
                if job_id:
                    logger.info(f"Job submitted successfully: {job_id}")
                    return job_id, data
                else:
                    raise RuntimeError("No job ID in response")
            else:
                if attempt == 0:
                    time.sleep(2)
                    continue
                raise RuntimeError(f"Submission failed: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            if attempt == 0:
                time.sleep(2)
                continue
            raise RuntimeError(f"Network error: {e}")
    
    raise RuntimeError("Max retries exceeded")


def poll_horde_job(job_id: str, poll_interval: float = 3.0, timeout: float = 180.0) -> Tuple[List[str], Dict]:
    """Poll AI Horde job status until completion."""
    start_time = time.time()
    status_url = STATUS_ENDPOINT.format(job_id)
    
    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Job {job_id} timed out after {timeout} seconds")
        
        try:
            response = requests.get(status_url, timeout=30)
            
            if response.status_code != 200:
                raise RuntimeError(f"Status check failed: {response.status_code} - {response.text}")
            
            data = response.json()
            is_done = data.get("done", False)
            
            if not data.get("is_possible", True):
                raise RuntimeError("Job marked as impossible by horde")
            
            if is_done:
                generations = data.get("generations", [])
                if not generations:
                    raise RuntimeError("Job completed but no images generated")
                
                images = [gen.get("img") for gen in generations if gen.get("img")]
                
                if not images:
                    raise RuntimeError("No valid images in completed job")
                
                logger.info(f"Job {job_id} completed with {len(images)} images")
                return images, data
            
            queue_position = data.get("queue_position", 0)
            if queue_position > 0:
                logger.info(f"Job {job_id} in queue position {queue_position}")
            
            time.sleep(poll_interval)
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network error during polling: {e}")


def b64_to_bytes(b64_str: str) -> bytes:
    """Convert base64 string or URL to bytes."""
    if b64_str.startswith("http"):
        response = requests.get(b64_str, timeout=30)
        if response.status_code == 200:
            return response.content
        else:
            raise RuntimeError(f"Failed to download image: {response.status_code}")
    
    if b64_str.startswith("data:"):
        b64_str = b64_str.split(",", 1)[1]
    
    return base64.b64decode(b64_str)


def generate_image_sync(prompt: str, model: str = "stable_diffusion", 
                       init_image_b64: Optional[str] = None, timeout: float = 300.0) -> bytes:
    """Generate image synchronously."""
    job_id, _ = submit_horde_job(prompt, model, init_image_b64)
    images_b64, _ = poll_horde_job(job_id, timeout=timeout)
    return b64_to_bytes(images_b64[0])