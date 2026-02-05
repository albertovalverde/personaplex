#!/usr/bin/env python3
import socket
import threading
import time
import struct
import json
import random
import math
import sys
import os
import subprocess

# Config
SERVER_IP = "127.0.0.1" # Localhost for simulation
PORT_AUDIO = 9001
PORT_VIDEO = 9002
PORT_CONTROL = 9003

# Check imports
try:
    from gtts import gTTS
    HAS_GTTS = True
except ImportError:
    HAS_GTTS = False
    print("Warning: gTTS not found. Chat will not generate audio.")

class PepperSimulator:
    def __init__(self):
        self.running = True
        self.audio_sock = None
        print(f"=== Pepper Simulator Starting (Target: {SERVER_IP}) ===")
        print("Type in the console to speak to Moshi (Requires gTTS+FFmpeg)")

    def connect_retry(self, port, name):
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((SERVER_IP, port))
                print(f"[{name}] Connected to port {port}")
                return s
            except ConnectionRefusedError:
                pass
            except Exception as e:
                print(f"[{name}] Error: {e}")
            time.sleep(2)
        return None

    def generate_and_send_audio(self, text):
        if not HAS_GTTS:
            print("[Error] gTTS not installed. Cannot speak.")
            return

        print(f"[Audio TX] Generating audio for: '{text}'...")
        try:
            # 1. Generate MP3
            tts = gTTS(text=text, lang='en')
            tts.save("temp_sim.mp3")
            
            # 2. Convert to PCM 24kHz Mono (Moshi Native)
            # Moshi usually wants 24000 for high quality, or 16000 via bridge.
            # Our bridge expects whatever. Let's send 24000 since we can.
            # But wait, Bridge might expect 16000 if we didn't implement resampling yet.
            # Bridge code I wrote: "Ideally convert 16k -> 24k here. But Moshi might just accept bytes..."
            # Let's send 24000 directly because Moshi is 24000 native.
            subprocess.run([
                "ffmpeg", "-y", "-v", "error",
                "-i", "temp_sim.mp3",
                "-f", "s16le", "-ar", "24000", "-ac", "1",
                "temp_sim.pcm"
            ], check=True)
            
            # 3. Read and Send
            if self.audio_sock:
                with open("temp_sim.pcm", "rb") as f:
                    data = f.read()
                    # Chunk it to simulate streaming?
                    chunk_size = 4096
                    for i in range(0, len(data), chunk_size):
                        self.audio_sock.sendall(data[i:i+chunk_size])
                        time.sleep(0.05) # Throttle slightly
                print("[Audio TX] Sent.")
            else:
                print("[Audio TX] Not connected.")
                
        except Exception as e:
            print(f"[Audio TX] Generation failed: {e}")

    def audio_tx_loop(self, sock):
        self.audio_sock = sock
        # Heartbeat silence to keep connection open
        try:
            while self.running:
                # Send 1s of silence every 1s if not speaking?
                # Actually, blocking on user input is handled in main loop.
                # Here we just keep the socket alive?
                # Or maybe we rely on the main loop to send.
                # Let's send a tiny KeepAlive silence byte
                time.sleep(1)
        except Exception:
            pass
        finally:
            pass

    def audio_rx_loop(self, sock):
        try:
            while self.running:
                data = sock.recv(4096)
                if not data: break
                # Visualizer hack
                # print(f"[Speaker] Received {len(data)} bytes")
        except Exception:
            pass

    def video_loop(self):
        sock = self.connect_retry(PORT_VIDEO, "Video")
        if not sock: return
        cnt = 0
        try:
            while self.running:
                # Fake payload
                payload = f"FAKE_FRAME_{cnt}".encode('utf-8') + b'.' * 50
                size = len(payload)
                header = struct.pack("!I", size)
                sock.sendall(header + payload)
                cnt += 1
                time.sleep(2.0) # Slower heartbeat
        except Exception:
            pass
        finally:
            sock.close()

    def control_loop(self):
        sock = self.connect_retry(PORT_CONTROL, "Control")
        if not sock: return
        f = sock.makefile()
        try:
            while self.running:
                line = f.readline()
                if not line: break
                print(f"\n[CONTROL] OM1 Says: {line.strip()}\n> ", end='', flush=True)
        except Exception:
            pass
        finally:
            sock.close()

    def input_loop(self):
        print("\n=== READY TO CHAT ===")
        print("Type something and press ENTER to speak to Moshi.")
        print(" Commands: /quit to exit")
        while self.running:
            try:
                # Use standard input
                sys.stdout.write("> ")
                sys.stdout.flush()
                text = sys.stdin.readline()
                if not text: break
                text = text.strip()
                
                if text == "/quit":
                    self.running = False
                    break
                
                if text:
                    # Run in thread to not block input?
                    # No, sequential is fine for simul.
                    self.generate_and_send_audio(text)
                    
            except KeyboardInterrupt:
                self.running = False

    def start(self):
        t_aud_rx = threading.Thread(target=lambda: self.connect_and_listen_audio())
        t_aud_rx.daemon = True
        t_aud_rx.start()

        t_vid = threading.Thread(target=self.video_loop)
        t_vid.daemon = True
        t_vid.start()
        
        t_ctrl = threading.Thread(target=self.control_loop)
        t_ctrl.daemon = True
        t_ctrl.start()
        
        # Main Thread = Input Loop
        self.input_loop()

    def connect_and_listen_audio(self):
        sock = self.connect_retry(PORT_AUDIO, "Audio")
        if sock:
            self.audio_sock = sock
            self.audio_rx_loop(sock)

if __name__ == "__main__":
    sim = PepperSimulator()
    sim.start()
