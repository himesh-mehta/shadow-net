"""Telemetry and microphone chunks use the same detector path as WAV uploads."""
import json
import logging
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from app.db import get_db
from app.audio.preprocessing import decode_base64_audio
from app.ml.factory import detector_status
from app.routers.audio import _process_audio_pipeline
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket Real-Time"])


@router.websocket("/ws/detection/{session_id}")
async def detection_websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(websocket, session_id)
    try:
        await websocket.send_json({"type": "connection_established", "session_id": session_id,
                                   **detector_status(), "status": "ready", "timestamp": time.time()})
        while True:
            try:
                msg = json.loads(await websocket.receive_text())
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                    continue
                if msg.get("type") != "audio_chunk" or not msg.get("audio_base64"):
                    raise ValueError("Expected an audio_chunk containing a WAV audio_base64 field.")
                result = await _process_audio_pipeline(decode_base64_audio(msg["audio_base64"]),
                                                       session_id=session_id, db=get_db())
                packet = result.model_dump(mode="json")
                packet.update(type="prediction_update", latency_ms=result.detection_latency_ms,
                              top_reason=result.explanation.get("top_reason", ""), timestamp=time.time())
                await websocket.send_json(packet)
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                logger.warning("Audio chunk failed: %s", exc)
                await websocket.send_json({"type": "error", "message": str(exc.detail) if isinstance(exc, HTTPException) else str(exc)})
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, session_id)
