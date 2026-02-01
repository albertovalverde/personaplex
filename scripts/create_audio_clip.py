import argparse
import os
from pydub import AudioSegment

def main():
    parser = argparse.ArgumentParser(description="Slice an audio file to a specific duration.")
    parser.add_argument("--input", type=str, required=True, help="Path to input audio file")
    parser.add_argument("--output", type=str, required=True, help="Path to save output audio file")
    parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds (default: 0)")
    parser.add_argument("--duration", type=float, default=20.0, help="Duration in seconds (default: 20)")
    
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ Error: Input file '{args.input}' not found.")
        return

    print(f"✂️  Loading {args.input}...")
    try:
        audio = AudioSegment.from_file(args.input)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return

    # pydub works in milliseconds
    start_ms = int(args.start * 1000)
    end_ms = start_ms + int(args.duration * 1000)

    # Check bounds
    if start_ms >= len(audio):
        print(f"❌ Error: Start time ({args.start}s) is beyond audio length ({len(audio)/1000:.2f}s).")
        return

    # Clip
    clipped_audio = audio[start_ms:end_ms]
    
    # Export
    print(f"💾 Saving {args.duration}s clip to {args.output}...")
    out_format = os.path.splitext(args.output)[1][1:] # get extension without dot
    if not out_format:
        out_format = "wav" # default
        
    clipped_audio.export(args.output, format=out_format)
    print("✅ Done!")

if __name__ == "__main__":
    main()
