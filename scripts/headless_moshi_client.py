#!/usr/bin/env python3
import asyncio
import aiohttp
import sys
import ssl
import json
import logging

# Config
MOSHI_URL = "wss://localhost:8998/api/chat"
SSL_VERIFY = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("headless_brain")

async def run_headless_brain():
    logger.info("Starting Headless Brain (Production Mode)...")
    
    # Connection Params matching Web UI
    params = {
        "text_temperature": 0.7,
        "text_topk": 25,
        "audio_temperature": 0.8,
        "audio_topk": 250,
        "pad_mult": 0,
        # "text_seed": random...,
        "text_prompt": "You are a helpful robot assistant.",
        "voice_prompt": "pepper.pt" # Ensure this exists on server
    }
    
    # SSL Context
    ssl_ctx = ssl.create_default_context()
    if not SSL_VERIFY:
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(MOSHI_URL, params=params, ssl=ssl_ctx) as ws:
                logger.info("Connected to Moshi Brain! Robot is now ALIVE.")
                logger.info("Press Ctrl+C to kill the brain.")
                
                # Handshake
                # Web UI sends initial empty bytes or similar?
                # Actually, the server starts sending. We just need to keep reading.
                
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.BINARY:
                        # We received audio/data from Moshi.
                        # Since we are headless, we usually ignore this audio 
                        # because the Server is ALREADY publishing it to Zenoh for the robot.
                        # This client exists JUST to tick the loop.
                        pass
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print("ws connection closed with exception %s", ws.exception())

        except Exception as e:
            logger.error(f"Brain died: {e}")
            logger.info("Retrying in 5s...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_headless_brain())
    except KeyboardInterrupt:
        pass
