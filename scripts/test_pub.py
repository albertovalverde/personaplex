import zenoh
import time

conf = zenoh.Config()
session = zenoh.open(conf)
pub = session.declare_publisher("pepper/audio/transcription")

print("Publishing test message...")
pub.put("TEST_TRANSCRIPTION")
session.close()
