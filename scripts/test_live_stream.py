import asyncio
import base64
import json
import os
import httpx
import websockets

async def test_streaming(target_lang: str, voice_id: str):
    id_token = os.environ.get("S2ST_TEST_FIREBASE_ID_TOKEN")
    if not id_token:
        raise SystemExit("Set S2ST_TEST_FIREBASE_ID_TOKEN to a real Firebase ID token")
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "http://127.0.0.1:8000/v1/sessions",
            json={
                "consented_audio_processing": True,
                "target_language": target_lang,
                "voice_id": voice_id,
            },
            headers={"Authorization": f"Bearer {id_token}"},
        )
        data = res.json()
        session_id = data["session_id"]
        ws_url = f"ws://127.0.0.1:8000{data['websocket']}"

        async with websockets.connect(ws_url, max_size=16 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"event": "auth", "id_token": id_token}))
            ready = json.loads(await ws.recv())
            if ready.get("event") != "ready":
                raise RuntimeError(ready.get("error", "WebSocket authentication failed"))
            # Send 1.5 seconds of synthetic 16 kHz audio
            pcm = b"\x10\x00" * 12000
            b64 = base64.b64encode(pcm).decode()
            await ws.send(json.dumps({"event": "audio", "pcm16le_base64": b64}))
            await ws.send(json.dumps({"event": "finalize", "voice_id": voice_id}))
            resp_str = await ws.recv()
            resp = json.loads(resp_str)
            wav_bytes = base64.b64decode(resp["wav_base64"])
            print(f"[OK] LIVE WS SUCCESS [{target_lang.upper()} - {resp['target_language_name']}]: Voice={resp['voice_id']} Latency={resp['latency_ms']}ms OutputWAV={len(wav_bytes)} bytes")

async def main():
    print("Testing live S2ST translation stream for Odia and Telugu:")
    await test_streaming("or", "or-IN-SukantNeural")
    await test_streaming("te", "te-IN-MohanNeural")
    await test_streaming("hi", "hi-IN-MadhurNeural")
    await test_streaming("en", "en-IN-PrabhatNeural")

if __name__ == "__main__":
    asyncio.run(main())
