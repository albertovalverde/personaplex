import os
import torch
import asyncio
import argparse
from pathlib import Path
import sys

# Add moshi path
sys.path.insert(0, os.path.abspath('moshi'))

from moshi.models import loaders
from moshi.models.lm import LMGen

async def main():
    parser = argparse.ArgumentParser(description="Generate PersonaPlex Voice Embedding (.pt) from .wav")
    parser.add_argument("--input", type=str, required=True, help="Path to input .wav file")
    parser.add_argument("--output", type=str, required=True, help="Path to save output .pt file")
    parser.add_argument("--weights", type=str, default="weights", help="Directory with model weights")
    args = parser.parse_args()

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    weights_dir = Path(args.weights)
    
    print(f"🎬 Loading models on {device}...")
    mimi = loaders.get_mimi(weights_dir / loaders.MIMI_NAME, device)
    moshi_lm = loaders.get_moshi_lm(weights_dir / loaders.MOSHI_NAME, device=device, cpu_offload=True)
    
    lm_gen = LMGen(moshi_lm, device=device, sample_rate=loaders.SAMPLE_RATE, save_voice_prompt_embeddings=True)

    print(f"🧬 Extracting voice signature from: {args.input}")
    # 1. Load the wav file into the model's memory
    lm_gen.load_voice_prompt(args.input)

    # 2. Process the audio to generate the internal state (the 'embedding')
    # This step 'conditions' the model
    with lm_gen.streaming(batch_size=1):
        await lm_gen.step_system_prompts_async(mimi)

    # 3. LMGen saves the file automatically to {input_filename}.pt
    # We rename it to the requested output path
    default_output = os.path.splitext(args.input)[0] + ".pt"
    
    if os.path.abspath(default_output) != os.path.abspath(args.output):
        if os.path.exists(default_output):
            os.rename(default_output, args.output)
            print(f"✅ Renamed {default_output} to {args.output}")
        else:
            print(f"❌ Error: Expected output file {default_output} not found.")
            sys.exit(1)
            
    print(f"✅ Success! Voice embedding saved as: {args.output}")
    print(f"✅ Success! Voice embedding saved as: {args.output}")
    print(f"💡 You can now use this file in the local inference notebook.")

if __name__ == "__main__":
    asyncio.run(main())
