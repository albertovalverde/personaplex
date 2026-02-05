import argparse
import asyncio
import logging
import os
import sys
import json
from pathlib import Path

import numpy as np
import torch
import zenoh
import sentencepiece
from huggingface_hub import hf_hub_download

# Add moshi to path
# The structure is personaplex/moshi/moshi
# We want to be able to do 'from moshi.models import loaders'
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "moshi"))

try:
    from moshi.models import loaders, MimiModel, LMModel, LMGen
except ImportError as e:
    print(f"Error importing moshi components: {e}")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("zenoh_bridge")

# Zenoh Topics
MIC_TOPIC = "pepper/audio/mic"
SPEAKER_TOPIC = "pepper/audio/speaker"
CONTROL_TOPIC = "pepper/personaplex/control"

class ZenohBridge:
    def __init__(self, mimi, other_mimi, text_tokenizer, lm, device, voice_prompt_path, text_prompt):
        self.mimi = mimi
        self.other_mimi = other_mimi
        self.text_tokenizer = text_tokenizer
        self.device = device
        self.frame_size = int(self.mimi.sample_rate / self.mimi.frame_rate)
        
        self.lm_gen = LMGen(lm,
                            audio_silence_frame_cnt=int(0.5 * self.mimi.frame_rate),
                            sample_rate=self.mimi.sample_rate,
                            device=device,
                            frame_rate=self.mimi.frame_rate)
        
        self.mimi.streaming_forever(1)
        self.other_mimi.streaming_forever(1)
        self.lm_gen.streaming_forever(1)
        
        self.voice_prompt_path = voice_prompt_path
        self.text_prompt = text_prompt
        
        self.input_queue = asyncio.Queue()
        self.running = True

    async def warmup(self):
        logger.info("Warming up model...")
        for _ in range(4):
            chunk = torch.zeros(1, 1, self.frame_size, dtype=torch.float32, device=self.device)
            codes = self.mimi.encode(chunk)
            _ = self.other_mimi.encode(chunk)
            for c in range(codes.shape[-1]):
                tokens = self.lm_gen.step(codes[:, :, c : c + 1])
                if tokens is None:
                    continue
                _ = self.mimi.decode(tokens[:, 1:9])
                _ = self.other_mimi.decode(tokens[:, 1:9])
        
        if self.device.type == 'cuda':
            torch.cuda.synchronize()
        
        logger.info("Initializing system prompts (loading voice/text prompts)...")
        # Load prompts
        if self.voice_prompt_path:
            if self.voice_prompt_path.endswith('.pt'):
                self.lm_gen.load_voice_prompt_embeddings(self.voice_prompt_path)
            else:
                self.lm_gen.load_voice_prompt(self.voice_prompt_path)
        
        if self.text_prompt:
             # wrap_with_system_tags logic
             cleaned = self.text_prompt.strip()
             if not (cleaned.startswith("<system>") and cleaned.endswith("<system>")):
                 processed_text_prompt = f"<system> {cleaned} <system>"
             else:
                 processed_text_prompt = cleaned
             self.lm_gen.text_prompt_tokens = self.text_tokenizer.encode(processed_text_prompt)

        # Step system prompts
        await self.lm_gen.step_system_prompts_async(self.mimi)
        self.mimi.reset_streaming()
        logger.info("Bridge ready.")

    def on_mic_data(self, sample):
        try:
            # Assume 24kHz mono 16-bit PCM for now.
            # Convert bytes to float32 [-1.0, 1.0]
            data = np.frombuffer(sample.payload, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Push to queue safely for the event loop
            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(self.input_queue.put_nowait, data)
            except RuntimeError:
                # No running loop yet or different thread
                pass
        except Exception as e:
            logger.error(f"Error in on_mic_data: {e}")

    def on_control_data(self, sample):
        try:
            payload = sample.payload.to_string()
            msg = json.loads(payload)
            command = msg.get("command")
            logger.info(f"Received control command: {command}")
            # Placeholder for future command implementation (filler, say, etc.)
        except Exception as e:
            logger.error(f"Error in on_control_data: {e}")

    async def run_loop(self, session):
        publisher = session.declare_publisher(SPEAKER_TOPIC)
        buffer = np.array([], dtype=np.float32)
        
        logger.info("Starting processing loop...")
        while self.running:
            try:
                # Get data from queue
                while len(buffer) < self.frame_size:
                    new_data = await self.input_queue.get()
                    buffer = np.concatenate((buffer, new_data))
                
                chunk = buffer[:self.frame_size]
                buffer = buffer[self.frame_size:]
                
                # Process with Moshi
                with torch.no_grad():
                    chunk_t = torch.from_numpy(chunk).to(self.device)[None, None]
                    codes = self.mimi.encode(chunk_t)
                    _ = self.other_mimi.encode(chunk_t)
                    
                    for c in range(codes.shape[-1]):
                        tokens = self.lm_gen.step(codes[:, :, c : c + 1])
                        if tokens is None:
                            continue
                        
                        # Decode agent audio (codebooks 1..8)
                        agent_audio_tokens = tokens[:, 1:9]
                        pcm_t = self.mimi.decode(agent_audio_tokens)
                        _ = self.other_mimi.decode(agent_audio_tokens)
                        
                        # Convert to 16-bit PCM mono
                        pcm = pcm_t.detach().cpu().numpy()[0, 0]
                        pcm_int16 = (pcm * 32767).clip(-32768, 32767).astype(np.int16).tobytes()
                        
                        # Publish to Zenoh
                        publisher.put(pcm_int16)
                        
                        # Log text tokens (k=0)
                        text_token = tokens[0, 0, 0].item()
                        if text_token not in (0, 3): # 0=EPAD, 3=PAD
                            text = self.text_tokenizer.id_to_piece(text_token)
                            text = text.replace("▁", " ")
                            if text.strip():
                                print(f"{text}", end="", flush=True)

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(0.1)

async def main():
    parser = argparse.ArgumentParser(description="Zenoh Bridge for Moshi (PersonaPlex) - OM1 Integration")
    parser.add_argument("--voice-prompt", type=str, default="voices/pepper.pt", help="Path to voice prompt .pt file")
    parser.add_argument("--text-prompt", type=str, default="You are Pepper, a friendly humanoid robot. Speak in Spanish as a default, but adapt to the user.", help="Initial text prompt")
    parser.add_argument("--device", type=str, default="cuda", help="cuda or cpu")
    parser.add_argument("--hf-repo", type=str, default=loaders.DEFAULT_REPO, help="HuggingFace repo for weights")
    parser.add_argument("--cpu-offload", action="store_true", help="Offload to CPU if GPU memory is low")
    
    args = parser.parse_args()

    # Device setup
    if args.device == "cuda" and not torch.cuda.is_available():
        logger.warning("CUDA not available, falling back to CPU")
        args.device = "cpu"
    device = torch.device(args.device)
    
    # Ensure voice prompt exists
    if not os.path.exists(args.voice_prompt):
        logger.warning(f"Voice prompt {args.voice_prompt} not found. Using default if available or skipping.")
        if not os.path.exists("voices"):
             os.makedirs("voices", exist_ok=True)

    # Load Models
    logger.info("Fetching weights from HuggingFace...")
    try:
        mimi_weight = hf_hub_download(args.hf_repo, loaders.MIMI_NAME)
        tokenizer_path = hf_hub_download(args.hf_repo, loaders.TEXT_TOKENIZER_NAME)
        moshi_weight = hf_hub_download(args.hf_repo, loaders.MOSHI_NAME)
    except Exception as e:
        logger.error(f"Failed to download weights: {e}")
        return

    logger.info("Loading Mimi...")
    mimi = loaders.get_mimi(mimi_weight, device)
    other_mimi = loaders.get_mimi(mimi_weight, device)
    
    logger.info("Loading Tokenizer...")
    text_tokenizer = sentencepiece.SentencePieceProcessor(tokenizer_path)
    
    logger.info("Loading Moshi LM...")
    lm = loaders.get_moshi_lm(moshi_weight, device=device, cpu_offload=args.cpu_offload)
    lm.eval()
    
    bridge = ZenohBridge(mimi, other_mimi, text_tokenizer, lm, device, args.voice_prompt, args.text_prompt)
    await bridge.warmup()
    
    # Zenoh Session
    logger.info("Opening Zenoh session...")
    conf = zenoh.Config()
    session = zenoh.open(conf)
    
    # Subscriptions
    sub_mic = session.declare_subscriber(MIC_TOPIC, bridge.on_mic_data)
    sub_ctrl = session.declare_subscriber(CONTROL_TOPIC, bridge.on_control_data)
    
    logger.info(f"Subscribed to {MIC_TOPIC} and {CONTROL_TOPIC}")
    logger.info(f"Publishing to {SPEAKER_TOPIC}")
    
    try:
        await bridge.run_loop(session)
    except asyncio.CancelledError:
        logger.info("Shutting down...")
    finally:
        bridge.running = False
        session.close()
        logger.info("Zenoh session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
