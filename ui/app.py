# python ui/app.py

import gradio as gr
import requests
from PIL import Image
import io
import base64
from typing import Optional, Tuple, Dict

BACKEND_URL = "http://localhost:8000"
EMOTIONS = ["happy", "sad", "angry", "surprised", "neutral", "disgust", "fear"]
STYLES = ["photorealistic", "cartoon", "oil"]

def detect_emotion(image) -> Tuple[str, str, Dict]:
    """Detect emotion in uploaded image."""
    if image is None:
        return "", "No image provided", {}
    
    try:
        # Convert PIL image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        
        # Send to backend
        files = {"image": ("image.jpg", img_bytes, "image/jpeg")}
        response = requests.post(f"{BACKEND_URL}/api/detect-emotion", files=files)
        
        if response.status_code == 200:
            data = response.json()
            emotion = data["dominant_emotion"]
            confidence = data["confidence"]
            
            # Format display text
            display_text = f"Detected: {emotion} — {confidence:.0%}"
            
            if confidence < 0.6:
                status = "Not confident — please pick an emotion"
            else:
                status = "Detection complete"
                
            return display_text, status, data["all_scores"]
        else:
            return "", f"Error: {response.text}", {}
            
    except Exception as e:
        return "", f"Error detecting emotion: {str(e)}", {}

def modify_image(image, target_emotion: str, intensity: float) -> Tuple[Optional[Image.Image], str]:
    """Modify original image with target emotion."""
    if image is None:
        return None, "No image provided"
    
    if not target_emotion:
        return None, "Please select a target emotion"
    
    try:
        # Convert image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_bytes = img_byte_arr.getvalue()
        
        # Send to backend
        files = {"image": ("image.jpg", img_bytes, "image/jpeg")}
        data = {
            "target_emotion": target_emotion,
            "intensity": intensity
        }
        
        response = requests.post(f"{BACKEND_URL}/api/edit-image", files=files, data=data)
        
        if response.status_code == 200:
            # Convert response bytes to PIL Image
            result_image = Image.open(io.BytesIO(response.content))
            return result_image, f"Modified to {target_emotion} (intensity: {intensity:.1f})"
        elif response.status_code == 501:
            return None, "Image editing not yet implemented"
        else:
            return None, f"Error: {response.text}"
            
    except Exception as e:
        return None, f"Error modifying image: {str(e)}"

def generate_image(seed_image, target_emotion: str, style: str) -> Tuple[Optional[Image.Image], str]:
    """Generate new image with target emotion."""
    if not target_emotion:
        return None, "Please select a target emotion"
    
    try:
        files = {}
        data = {
            "target_emotion": target_emotion,
            "style": style
        }
        
        # Add seed image if provided
        if seed_image is not None:
            img_byte_arr = io.BytesIO()
            seed_image.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()
            files["image"] = ("image.jpg", img_bytes, "image/jpeg")
        
        response = requests.post(f"{BACKEND_URL}/api/generate-image", files=files, data=data)
        
        if response.status_code == 200:
            result_image = Image.open(io.BytesIO(response.content))
            seed_text = "with seed image" if seed_image else "without seed"
            return result_image, f"Generated {target_emotion} image ({style} style) {seed_text}"
        elif response.status_code == 501:
            return None, "Image generation not yet implemented"
        else:
            return None, f"Error: {response.text}"
            
    except Exception as e:
        return None, f"Error generating image: {str(e)}"

def create_emotion_buttons():
    """Create emotion selection buttons."""
    buttons = []
    for emotion in EMOTIONS:
        btn = gr.Button(emotion.capitalize(), size="sm")
        buttons.append(btn)
    return buttons

# Create Gradio interface
with gr.Blocks(title="Emotion Detection & Generation", theme=gr.themes.Soft()) as app:
    gr.Markdown("# Emotion Detection & Image Generation")
    gr.Markdown("Upload an image to detect emotions, then modify or generate new images")
    
    with gr.Row():
        with gr.Column(scale=1):
            # Image upload and detection
            input_image = gr.Image(label="Upload Image", type="pil")
            detect_btn = gr.Button("Detect Emotion", variant="primary")
            
            # Detection results
            detection_result = gr.Textbox(label="Detection Result", interactive=False)
            status_message = gr.Textbox(label="Status", interactive=False)
            
            # Emotion scores display
            scores_display = gr.JSON(label="All Emotion Scores", visible=False)
            
        with gr.Column(scale=1):
            # Controls
            gr.Markdown("### Select Target Emotion")
            selected_emotion = gr.Textbox(label="Target Emotion", interactive=False)
            
            with gr.Row():
                emotion_buttons = create_emotion_buttons()
            
            intensity_slider = gr.Slider(
                minimum=0.0, 
                maximum=1.0, 
                value=0.5, 
                step=0.1,
                label="Intensity"
            )
            
            style_dropdown = gr.Dropdown(
                choices=STYLES,
                value="photorealistic",
                label="Generation Style"
            )
            
            # Action buttons
            with gr.Row():
                modify_btn = gr.Button("Modify Original", variant="secondary")
                generate_btn = gr.Button("Generate New Image", variant="secondary")
    
    # Results section
    with gr.Row():
        with gr.Column():
            modified_image = gr.Image(label="Modified Image")
            modify_status = gr.Textbox(label="Modification Status", interactive=False)
            modify_download = gr.DownloadButton("Download Modified", visible=False)
        
        with gr.Column():
            generated_image = gr.Image(label="Generated Image")
            generate_status = gr.Textbox(label="Generation Status", interactive=False)
            generate_download = gr.DownloadButton("Download Generated", visible=False)
    
    # Event handlers
    def on_detect(image):
        result = detect_emotion(image)
        scores_visible = len(result[2]) > 0
        return result[0], result[1], gr.update(value=result[2], visible=scores_visible)
    
    def on_emotion_select(emotion_name):
        return emotion_name
    
    def on_modify(image, emotion, intensity):
        if not emotion:
            return None, "Please select a target emotion first", gr.update(visible=False)
        
        result_img, status = modify_image(image, emotion, intensity)
        download_visible = result_img is not None
        return result_img, status, gr.update(visible=download_visible)
    
    def on_generate(seed_image, emotion, style):
        if not emotion:
            return None, "Please select a target emotion first", gr.update(visible=False)
        
        result_img, status = generate_image(seed_image, emotion, style)
        download_visible = result_img is not None
        return result_img, status, gr.update(visible=download_visible)
    
    # Wire up events
    detect_btn.click(
        on_detect,
        inputs=[input_image],
        outputs=[detection_result, status_message, scores_display]
    )
    
    input_image.change(
        on_detect,
        inputs=[input_image],
        outputs=[detection_result, status_message, scores_display]
    )
    
    # Emotion button events
    for i, btn in enumerate(emotion_buttons):
        emotion_name = EMOTIONS[i]
        btn.click(
            lambda name=emotion_name: name,
            outputs=[selected_emotion]
        )
    
    modify_btn.click(
        on_modify,
        inputs=[input_image, selected_emotion, intensity_slider],
        outputs=[modified_image, modify_status, modify_download]
    )
    
    generate_btn.click(
        on_generate,
        inputs=[input_image, selected_emotion, style_dropdown],
        outputs=[generated_image, generate_status, generate_download]
    )

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)