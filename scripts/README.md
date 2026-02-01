# Scripts Directory

This directory contains utility scripts for managing the PersonaPlex environment, generating voice embeddings, and handling model weights.

## 1. `generate_voice_embedding.py` (Recommended)
The main script for generating voice embeddings (`.pt` files) from audio files.
- **Usage:**
  ```bash
  python generate_voice_embedding.py --input <audio_file> --output <output_file.pt> --weights <weights_dir>
  ```
- **Features:** Supports custom weights directory, handles audio loading, and generates the necessary embedding file for voice cloning.



## 3. `create_audio_clip.py`
Helper to slice audio files (e.g., keep only the first 20 seconds).
- **Usage:**
  ```bash
  python create_audio_clip.py --input assets/test/raw.mp3 --output assets/test/clip.mp3 --start 0 --duration 20
  ```

## 4. `copy_voice_pt.sh`
A helper shell script to copy the generated `pepper.pt` to the Hugging Face cache directory used by the server.
- **Usage:** `./copy_voice_pt.sh`
- **Note:** Modify the `DEST_DIR` variable if your cache path differs.

## 5. `download_weights_local.py`
Downloads the PersonaPlex model weights to a local `weights/` directory.
- **Usage:** `python download_weights_local.py`
- **Features:** Bypasses SSL verification for environments with certificate issues.

---

For a detailed guide on creating voice embeddings, see [VOICE_EMBEDDING_GENERATION.md](./VOICE_EMBEDDING_GENERATION.md).
