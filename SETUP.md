# ASL Interpreter — Complete Setup Guide

## What This App Does

- Your webcam captures hand signs + facial expressions in real time
- **MediaPipe** extracts 21 hand landmarks and 468 face landmarks per frame
- Facial expressions (raised eyebrows, puffed cheeks, mouth open, etc.) are mapped to **ASL grammatical modifiers** — because in ASL, a raised brow turns a statement into a yes/no question
- After a 2-second pause, the sign sequence + expressions are sent to a **local Ollama LLM**
- The LLM returns a natural English translation; words it added or changed to fix grammar are **underlined** in the UI

---

## Prerequisites

| Tool | Why needed | Link |
|------|-----------|------|
| Python 3.10+ | Runs the detector & LLM bridge | https://python.org |
| Node.js 18+ | Runs Electron (the desktop app) | https://nodejs.org |
| Ollama | Local LLM inference (no API key needed) | https://ollama.com |
| A webcam | Sign detection | — |

---

## Step 1 — Install Python dependencies

Open a terminal in the project folder:

```bash
cd asl-translator

# Create a virtual environment (recommended)
python3 -m venv .venv

# Activate it
# macOS / Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install Python packages
pip install -r backend/requirements.txt
```

This installs:
- `mediapipe` — Google's ML framework for hand/face landmark detection
- `opencv-python` — camera capture
- `numpy` — math utilities
- `requests` — HTTP calls to Ollama

---

## Step 2 — Install and start Ollama

### 2a. Download Ollama

Go to **https://ollama.com/download** and install for your OS.

### 2b. Pull a model

```bash
# Llama 3 (recommended, ~4.7 GB)
ollama pull llama3

# Or a smaller model if you have limited RAM:
ollama pull llama3.2      # ~2 GB
ollama pull mistral       # ~4 GB
ollama pull phi3          # ~2.3 GB
```

### 2c. Start the Ollama server

```bash
ollama serve
```

Leave this terminal open. Ollama runs at `http://localhost:11434`.

> **Changing the model:** Open `backend/llm_bridge.py` and change line 11:
> ```python
> OLLAMA_MODEL = "llama3"   # ← change to your pulled model name
> ```

---

## Step 3 — Install Node.js / Electron

```bash
# In the asl-translator folder
npm install
```

This downloads Electron and electron-builder locally.

---

## Step 4 — Run the app

```bash
npm start
```

The Electron window opens. It automatically:
1. Opens your webcam
2. Spawns `asl_detector.py` as a background process
3. Spawns `llm_bridge.py` as a background process
4. The two Python processes communicate through the Electron main process

---

## How to use it

1. **Position yourself** so your face and at least one hand are visible
2. **Make an ASL sign** — the sign appears over the camera feed and as a chip in the sequence strip
3. **Hold signs** for a moment before switching — the gesture smoother needs a few frames
4. **Pause for 2 seconds** with no new sign → the sequence is sent to Ollama for translation
5. The **English translation** appears in the right panel
6. **Underlined words** are ones the AI added/changed to make the English natural
7. **Green pills** show detected facial expressions
8. **Coloured chips** show grammatical modifiers (blue = question, amber = intensity, red = negation)

---

## Supported signs (built-in)

| Sign | Gesture |
|------|---------|
| A | Fist |
| B | Four fingers extended, thumb folded |
| 1 | Index finger only |
| 2 | Index + middle (together) |
| 3 | Index + middle + ring |
| 4 | All fingers except thumb |
| 5 / Open hand | All five fingers |
| V / Peace | Index + middle spread apart |
| L | Thumb + index extended at 90° |
| I | Pinky only |
| D | Index + thumb circle |
| OK | Thumb + index pinch, others extended |
| ILY | Thumb + index + pinky (I Love You) |
| HORNS | Index + pinky + thumb |

> The gesture classifier is in `backend/asl_detector.py` — you can add more signs in the `classify_hand_gesture()` function.

---

## Facial expressions mapped to ASL grammar

| Expression | ASL meaning | Effect on translation |
|-----------|-------------|----------------------|
| Raised eyebrows | Yes/no question marker | LLM turns statement into a yes/no question |
| Furrowed brows | Wh-question marker | LLM uses who/what/where/when/why phrasing |
| Puffed cheeks | Large size / intensity | LLM adds "very", "huge", intensity words |
| Wide open mouth | Extreme / shocked | LLM reflects surprise or extremity |
| Smile | Positive sentiment | LLM uses positive, warm language |
| Grimace | Negative / difficult | LLM reflects difficulty or negativity |
| Head tilt left/right | Topicalization | LLM may reframe as topic-comment |
| Squinted eyes | Negation / intensity | LLM considers negation or strong emphasis |

---

## Troubleshooting

### "Cannot open camera"
- Make sure no other app (Zoom, Teams) is using your webcam
- On macOS: System Settings → Privacy & Security → Camera → grant Electron access
- On Windows: Settings → Privacy → Camera → allow apps

### Ollama not responding / translation shows "[Ollama not running]"
- Run `ollama serve` in a separate terminal
- Check it's running: `curl http://localhost:11434/api/version`
- Make sure you pulled a model: `ollama list`

### Signs not detected
- Ensure good lighting; MediaPipe struggles in low light
- Keep your hand 40–70 cm from the camera
- Plain background helps detection

### Wrong model name error
- Run `ollama list` to see installed models
- Update `OLLAMA_MODEL` in `backend/llm_bridge.py` to match exactly

### Python not found on Windows
- Use `python` instead of `python3`
- Or set the path in `frontend/main.js`: change `"python3"` to `"python"` on line 12

---

## Project structure

```
asl-translator/
├── backend/
│   ├── asl_detector.py   # MediaPipe hand + face capture → JSON events
│   ├── llm_bridge.py     # Ollama query + translation formatting
│   └── requirements.txt
├── frontend/
│   ├── main.js           # Electron main process (spawns Python, bridges IPC)
│   ├── preload.js        # Secure context bridge
│   └── index.html        # Full UI (camera, sequence, translation)
├── package.json
└── SETUP.md              # This file
```

---

## Extending the app

### Add a new sign
In `backend/asl_detector.py`, inside `classify_hand_gesture()`:
```python
# fingers = [thumb, index, middle, ring, pinky]
if fingers == [True, True, True, False, False]:
    return "W"   # example
```

### Add a new facial expression
In `analyse_face()`, compute a new geometric condition and append to `expressions` and `modifiers`.

### Change the LLM prompt
Edit `SYSTEM_PROMPT` in `backend/llm_bridge.py` to change translation style, formality, or add domain-specific context.

### Use a different LLM provider
Replace `query_ollama()` in `llm_bridge.py` with any HTTP call — OpenAI, Anthropic, Groq, etc.
