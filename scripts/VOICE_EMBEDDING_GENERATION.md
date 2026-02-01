# Voice Embedding Generation Guide

This guide explains how to create a high-quality voice embedding (`.pt` file) for PersonaPlex using the `generate_voice_embedding.py` script.

## 1. Prepare Your Audio
The quality of the voice clone depends heavily on the input audio.
- **Duration:** 10-20 seconds is optimal. Longer files take longer to process and may not improve quality.
- **Format:** WAV or MP3 (Mono or Stereo). The script re-samples it to 24kHz automatically.
- **Content:** A clear voice sample with minimal background noise.
- **Trimming:** If your audio has a long silence at the beginning, trim it. The model might clone the silence instead of the voice if it starts with one.

**Example (using helper script):**
```bash
python ./scripts/create_audio_clip.py --input assets/test/original.mp3 --output assets/test/clip.mp3 --start 10 --duration 20
```
*(This extracts 20 seconds starting from the 10-second mark)*

## 2. Generate the Embedding
Run the `generate_voice_embedding.py` script from the project root.

```bash
./venv/bin/python ./scripts/generate_voice_embedding.py \
  --input ./assets/test/your_clip.mp3 \
  --output ./assets/test/your_voice.pt \
  --weights /path/to/weights
```

- `--input`: Path to your audio file.
- `--output`: Path where the `.pt` file will be saved.
- `--weights`: Path to the directory containing model weights (e.g., in HF cache).

**Example Command used for Pepper:**
```bash
./venv/bin/python ./scripts/generate_voice_embedding.py \
  --input ./assets/test/pepper.wav \
  --output ./assets/test/pepper_v2.pt \
  --weights /home/anls/.cache/huggingface/hub/models--nvidia--personaplex-7b-v1/snapshots/3343b641d663e4c851120b3575cbdfa4cc33e7fa
```

## 3. Using the Voice Embedding
The `.pt` file captures the **timbre** (voice sound) but NOT the **persona** (personality/speaking style).

### Offline Verification
To verify the voice behaves as expected:
```bash
python -m moshi.offline \
  --voice-prompt "your_voice.pt" \
  --voice-prompt-dir "./assets/test" \
  --text-prompt "You are a helpful robot..." \
  --input-wav "assets/test/input_clip.mp3" \
  --output-wav "output.wav"
```

```bash

python -m moshi.offline   --voice-prompt "pepper.pt"   --voice-prompt-dir "./voices"   --text-prompt "You are Pepper, a robot. You speak with a highly robotic, staccato, and flat intonation. You sound synthetic and mechanical."   --input-wav "assets/test/pepper_clip_v2.mp3"   --output-wav "output_pepper.wav"   --output-text "output_pepper.json"


```



### Full Server Usage
1. Copy the `.pt` file to the `voices/` directory used by the server.
2. Select the voice in the Web UI.
3. **CRITICAL:** You must provide a **Text Prompt** (System Prompt) in the UI or your client configuration to define the personality (e.g., "You are Pepper, a helpful robot..."). The voice embedding alone will not make it act like a robot.
