import asyncio
import os
import logging
import base64
import json
import traceback

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
async def get_frontend():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("favicon.ico")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected to the backend proxy.")

    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing.")

        ai_client = genai.Client(
            api_key=api_key,
            http_options={'api_version': 'v1alpha'}
        )

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part.from_text(
                    text="You are an expert, encouraging tutor for any subject. You can see the user's camera feed in real-time. When the user asks for help, look at the video frames to understand their screen or homework. Keep answers to 1 or 2 short sentences. Guide them to the answer, do not just give it to them."
                )]
            )
        )

        model_name = "gemini-2.5-flash-native-audio-preview-12-2025" 
        audio_queue = asyncio.Queue()

        async def read_from_client():
            try:
                while True:
                    msg = await websocket.receive()
                    if msg["type"] == "websocket.disconnect":
                        break
                    
                    if "bytes" in msg and msg.get("bytes"):
                        await audio_queue.put(("audio", msg["bytes"]))
                    elif "text" in msg and msg.get("text"):
                        await audio_queue.put(("video", msg["text"]))
                        
            except Exception as e:
                logger.info(f"User closed the browser tab or socket died.")

        client_task = asyncio.create_task(read_from_client(), name="ClientRead")

        while not client_task.done():
            try:
                logger.info("Dialing Gemini Live API...")
                async with ai_client.aio.live.connect(model=model_name, config=config) as session:
                    logger.info("Gemini connected! Ready for audio/vision conversation.")

                    async def send_to_gemini():
                        while True:
                            data_type, payload = await audio_queue.get()
                            
                            if data_type == "audio":
                                await session.send_realtime_input(
                                    audio=types.Blob(data=payload, mime_type="audio/pcm;rate=16000")
                                )
                            elif data_type == "video":
                                try:
                                    msg_json = json.loads(payload)
                                    b64_data = msg_json.get("data", "")
                                    
                                    if "," in b64_data:
                                        b64_data = b64_data.split(",")[1]
                                    
                                    frame_bytes = base64.b64decode(b64_data)
                                    
                                    await session.send_realtime_input(
                                        video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
                                    )
                                except Exception as e:
                                    logger.error(f"Error parsing video frame: {e}")

                    async def receive_from_gemini():
                        async for response in session.receive():
                            if response.server_content and response.server_content.model_turn:
                                for part in response.server_content.model_turn.parts:
                                    if part.inline_data and part.inline_data.data:
                                        await websocket.send_bytes(part.inline_data.data)

                    send_task = asyncio.create_task(send_to_gemini(), name="GeminiSend")
                    recv_task = asyncio.create_task(receive_from_gemini(), name="GeminiRecv")

                    done, pending = await asyncio.wait(
                        [send_task, recv_task, client_task], 
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    if client_task in done:
                        send_task.cancel()
                        recv_task.cancel()
                        break

                    send_task.cancel()
                    recv_task.cancel()
                    logger.warning("Gemini ended its turn. Auto-reconnecting...")

            except Exception as e:
                logger.error(f"Gemini connection dropped: {e}")
                await asyncio.sleep(0.5)

    except Exception as e:
        logger.error("Fatal proxy error", exc_info=True)
        
    finally:
        try:
            await websocket.close(code=1000)
        except Exception:
            pass