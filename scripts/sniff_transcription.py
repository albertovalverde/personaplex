import zenoh
import time

def listener(sample):
    print(f"Received: {sample.payload.to_string()}")

conf = zenoh.Config()
session = zenoh.open(conf)
sub = session.declare_subscriber("pepper/audio/transcription", listener)

print("Listening for transcription on 'pepper/audio/transcription'...")
time.sleep(30)
