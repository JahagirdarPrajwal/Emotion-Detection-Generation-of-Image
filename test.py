from gemini_client import call_gemini_multimodal, DETECT_PROMPT

# Load a real image file
with open("D:\\GenAIProj\\sadface.jpg", "rb") as f:
    image_bytes = f.read()

result = call_gemini_multimodal(DETECT_PROMPT, image_bytes, "detect")
print(result)  # Should show emotion detection results!