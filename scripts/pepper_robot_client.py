#! /usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import time
import socket
import struct
import threading
import json
import subprocess

# NAOqi imports (only work on robot)
try:
    import qi
    from naoqi import ALProxy
    HAS_NAOQI = True
except ImportError:
    HAS_NAOQI = False
    print "Warning: NAOqi not found. Running in standalone mode."

# Config
SERVER_IP = "127.0.0.1" # CHANGE THIS to Server IP
PORT_AUDIO = 9001
PORT_VIDEO = 9002
PORT_CONTROL = 9003

class PepperClient(object):
    def __init__(self, session=None):
        self.session = session
        self.running = True
        self.audio_sock = None
        
        if HAS_NAOQI and session:
            self.tts = self.session.service("ALTextToSpeech")
            self.motion = self.session.service("ALMotion")
        else:
            self.tts = None
            self.motion = None

    def connect_retry(self, port, name):
        while self.running:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)
                s.connect((SERVER_IP, port))
                print "[%s] Connected to %s:%s" % (name, SERVER_IP, port)
                return s
            except Exception as e:
                print "[%s] Connection failed, retrying... %s" % (name, e)
                time.sleep(3)
        return None

    def audio_rx_loop(self):
        """Receives audio from Moshi and plays it via aplay."""
        sock = self.connect_retry(PORT_AUDIO, "AudioRX")
        if not sock: return

        # Launch aplay in a subprocess
        # Moshi sends 24000Hz S16_LE Mono
        try:
            aplay = subprocess.Popen(
                ["aplay", "-f", "S16_LE", "-r", "24000", "-c", "1", "-t", "raw"],
                stdin=subprocess.PIPE
            )
            
            print "[Speaker] Listening for response..."
            while self.running:
                data = sock.recv(4096)
                if not data:
                    print "[Speaker] Connection closed."
                    break
                
                # Visualizer (Simulator improvement)
                sys.stdout.write("♪")
                sys.stdout.flush()
                
                # Play audio
                try:
                    aplay.stdin.write(data)
                except Exception:
                    break
        except Exception as e:
            print "[Speaker] Error: %s" % e
        finally:
            if sock: sock.close()
            try: aplay.terminate()
            except: pass

    def audio_tx_loop(self):
        """Captures audio from mic and sends to Moshi."""
        sock = self.connect_retry(PORT_AUDIO, "AudioTX")
        if not sock: return

        # arecord -f S16_LE -r 16000 -c 1 -t raw
        try:
            arecord = subprocess.Popen(
                ["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "raw"],
                stdout=subprocess.PIPE
            )
            
            print "[Mic] Streaming audio..."
            while self.running:
                data = arecord.stdout.read(2048)
                if not data: break
                sock.sendall(data)
        except Exception as e:
            print "[Mic] Error: %s" % e
        finally:
            if sock: sock.close()
            try: arecord.terminate()
            except: pass

    def control_loop(self):
        """Listens for JSON commands from OM1/Server."""
        sock = self.connect_retry(PORT_CONTROL, "Control")
        if not sock: return
        
        try:
            f = sock.makefile()
            while self.running:
                line = f.readline()
                if not line: break
                try:
                    msg = json.loads(line)
                    print "\n[Control] Received: %s" % msg
                    
                    if self.tts and msg.get("action") == "say":
                        self.tts.say(str(msg["text"]))
                        
                except Exception as e:
                    print "Control Parse Error: %s" % e
        finally:
            sock.close()

    def start(self):
        # Threads for I/O
        t_rx = threading.Thread(target=self.audio_rx_loop)
        t_tx = threading.Thread(target=self.audio_tx_loop)
        t_ctrl = threading.Thread(target=self.control_loop)
        
        t_rx.daemon = True
        t_tx.daemon = True
        t_ctrl.daemon = True
        
        t_rx.start()
        t_tx.start()
        t_ctrl.start()
        
        print "=== PEPPER CLIENT READY ==="
        print "Audio I/O active with visualizer (♪)"
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print "Stopping..."

if __name__ == "__main__":
    session = None
    if HAS_NAOQI:
        try:
            app = qi.Application(sys.argv)
            app.start()
            session = app.session
        except Exception as e:
            print "Could not start qi.Application: %s" % e
            
    client = PepperClient(session)
    client.start()
