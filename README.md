# Emotion Detection & Image Generation

A modern web application that uses AI to detect emotions in images and generate/modify images with different emotional expressions.

## Features

- **Emotion Detection**: Analyze facial expressions using Google Gemini AI
- **Image Modification**: Change emotions in existing photos
- **Image Generation**: Create new images with specific emotions
- **Web Interface**: User-friendly Gradio-based UI
- **Multiple Styles**: Support for photorealistic, cartoon, and oil painting styles

## Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key
- Stable Horde API key (optional, for better priority)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   STABLE_HORDE_API_KEY=your_stable_horde_key_here
   ```

### Running the Application

**Option 1: Use the launcher script**
```bash
python run.py
```

**Option 2: Manual startup**

Start the backend API (**RECOMMENDED** - use this one):
```bash
uvicorn src.api.main:app --reload --port 8000
```

Alternative backends (for reference):
```bash
# Original horde_handlers backend
uvicorn backend.horde_handlers:app --reload --port 8000

# Original basic backend (deprecated)
uvicorn backend.main:app --reload --port 8000
```

Start the frontend UI (in another terminal):
```bash
python src/ui/app.py
```

Then open http://localhost:7860 in your browser.

## Project Structure

```
src/
├── api/           # FastAPI backend (RECOMMENDED - cleaned horde_handlers.py)
│   └── main.py    # Main backend to use
├── clients/       # API clients (Gemini, Stable Horde)
│   ├── gemini_client.py
│   └── horde_client.py
└── ui/            # Gradio web interface
    └── app.py
tests/             # Test files and utilities
assets/            # Sample images and resources
backend/           # Original backend files (for reference)
├── horde_handlers.py  # Original working backend
└── main.py           # Original basic backend (deprecated)
```

**Which backend to use:**
- **`src/api/main.py`** ← **USE THIS ONE** (cleaned, organized version)
- `backend/horde_handlers.py` ← Original working version
- `backend/main.py` ← Deprecated basic version

## Supported Emotions

- Happy
- Sad  
- Angry
- Surprised
- Neutral
- Disgust
- Fear

## Usage Tips

### ⏱️ **Generation Times**
- **Image modification**: 30-60 seconds (depending on Stable Horde queue)
- **New image generation**: 45-90 seconds
- **Emotion detection**: 2-5 seconds

**Please be patient!** Image generation uses free Stable Horde service, so wait times can vary based on demand.

### 🎛️ **Intensity Recommendations**

| Emotion | Recommended Intensity | Effect |
|---------|---------------------|--------|
| **Happy** | 0.3 - 0.5 | Gentle smile to broad grin |
| **Sad** | 0.4 - 0.7 | Subtle melancholy to visible sadness |
| **Angry** | 0.5 - 0.8 | Stern look to intense anger |
| **Surprised** | 0.4 - 0.6 | Raised eyebrows to wide-eyed shock |
| **Neutral** | 0.2 - 0.4 | Calm to completely expressionless |
| **Disgust** | 0.3 - 0.6 | Slight disapproval to clear revulsion |
| **Fear** | 0.4 - 0.7 | Concern to visible fear |

**Intensity Scale:**
- `0.1-0.3`: Subtle changes
- `0.4-0.6`: Moderate changes (recommended)
- `0.7-1.0`: Strong changes (may look unnatural)

## API Endpoints

- `POST /api/detect-emotion` - Detect emotion in uploaded image
- `POST /api/edit-image` - Modify image with new emotion
- `POST /api/generate-image` - Generate new image with specific emotion

## Technologies Used

- **Google Gemini API** - Emotion detection
- **Stable Horde** - Image generation and modification
- **FastAPI** - Backend API framework
- **Gradio** - Web interface
- **Pillow** - Image processing

## Troubleshooting

### Common Issues:

**"Taking too long to generate"**
- Stable Horde is free but can be slow during peak hours
- Wait up to 3-5 minutes during busy periods
- Try again later if consistently timing out

**"Low confidence emotion detection"**
- Use clear, well-lit photos with visible faces
- Avoid blurry or dark images
- Face should be the main subject in the image

**"Connection errors"**
- Check your internet connection
- Verify API keys in `.env` file
- Restart the backend if needed

- Try different intensity levels (0.3-0.6 works best)
- Some emotions work better with certain face types
- Generation quality varies - try multiple times

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please read the code and follow the existing patterns.