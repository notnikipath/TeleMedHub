from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.telemed_common import (
    ConnectionQuality,
    Role,
    SessionStatus,
    Settings,
    VideoSession,
    VideoSessionRequest,
    analyze_complaint,
    has_permission,
    speech_to_protocol,
)

settings = Settings(service_name="consultation-service", service_port=8102)
app = FastAPI(title="TeleMedHub Consultation Service", version="1.0.0")

sessions: dict[str, VideoSession] = {}
chat_messages: dict[str, list[dict]] = defaultdict(list)
uploaded_files: dict[str, list[dict]] = defaultdict(list)
quality_events: dict[str, list[dict]] = defaultdict(list)
video_nodes = [
    {"name": "janus-node-1", "active_sessions": 0, "region": "ru-central"},
    {"name": "janus-node-2", "active_sessions": 0, "region": "ru-west"},
    {"name": "janus-node-3", "active_sessions": 0, "region": "kz-central"},
]


class SDPRequest(BaseModel):
    actor_role: Role
    sdp: str


class ChatMessageRequest(BaseModel):
    actor_id: str
    actor_role: Role
    message: str = Field(min_length=1, max_length=5000)


class FileUploadRequest(BaseModel):
    actor_id: str
    actor_role: Role
    filename: str
    content_type: str
    size_bytes: int = Field(gt=0, le=50_000_000)


class SessionEndRequest(BaseModel):
    actor_role: Role
    actor_id: str


class SpeechProtocolRequest(BaseModel):
    actor_id: str
    actor_role: Role
    transcript: str


class ComplaintAnalysisRequest(BaseModel):
    patient_id: str
    actor_role: Role
    text: str


SDPRequest.model_rebuild()
ChatMessageRequest.model_rebuild()
FileUploadRequest.model_rebuild()
SessionEndRequest.model_rebuild()
SpeechProtocolRequest.model_rebuild()
ComplaintAnalysisRequest.model_rebuild()


def _assert_doctor_or_patient(role: Role) -> None:
    allowed = {Role.DOCTOR, Role.PATIENT, Role.ADMIN}
    if role not in allowed:
        raise HTTPException(status_code=403, detail="Forbidden")


def _pick_video_node() -> str:
    selected = min(video_nodes, key=lambda node: node["active_sessions"])
    selected["active_sessions"] += 1
    return str(selected["name"])


def _release_video_node(node_name: str) -> None:
    for node in video_nodes:
        if node["name"] == node_name:
            node["active_sessions"] = max(0, int(node["active_sessions"]) - 1)
            return


async def _async_store_file(session_id: str, request: FileUploadRequest) -> None:
    await asyncio.sleep(0.05)
    uploaded_files[session_id].append(
        {
            "file_id": str(uuid4()),
            "filename": request.filename,
            "content_type": request.content_type,
            "size_bytes": request.size_bytes,
            "uploaded_by": request.actor_id,
            "uploaded_at": datetime.now(UTC).isoformat(),
        }
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/sessions/start")
async def start_session(request: VideoSessionRequest) -> dict:
    _assert_doctor_or_patient(request.actor_role)
    session_id = str(uuid4())
    session = VideoSession(
        session_id=session_id,
        appointment_id=request.appointment_id,
        status=SessionStatus.ACTIVE,
        selected_media_node=_pick_video_node(),
        consent_recording=request.consent_recording,
        started_at=datetime.now(UTC),
    )
    sessions[session_id] = session
    return session.model_dump(mode="json")


@app.post("/sessions/{session_id}/offer")
async def set_offer(session_id: str, request: SDPRequest) -> dict:
    _assert_doctor_or_patient(request.actor_role)
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.webrtc_offer = request.sdp
    return {"session_id": session_id, "status": "offer_received"}


@app.post("/sessions/{session_id}/answer")
async def set_answer(session_id: str, request: SDPRequest) -> dict:
    _assert_doctor_or_patient(request.actor_role)
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.webrtc_answer = request.sdp
    return {"session_id": session_id, "status": "answer_received"}


@app.post("/sessions/{session_id}/chat")
async def chat(session_id: str, request: ChatMessageRequest) -> dict:
    _assert_doctor_or_patient(request.actor_role)
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    item = {
        "id": str(uuid4()),
        "actor_id": request.actor_id,
        "actor_role": request.actor_role.value,
        "message": request.message,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    chat_messages[session_id].append(item)
    return item


@app.post("/sessions/{session_id}/files")
async def upload_file(session_id: str, request: FileUploadRequest, background: BackgroundTasks) -> dict:
    _assert_doctor_or_patient(request.actor_role)
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    background.add_task(_async_store_file, session_id, request)
    return {"status": "accepted", "session_id": session_id, "filename": request.filename}


@app.post("/sessions/{session_id}/quality")
async def report_quality(session_id: str, request: ConnectionQuality) -> dict:
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    quality_events[session_id].append(request.model_dump(mode="json"))
    degraded = request.latency_ms > settings.video_target_latency_ms or request.packet_loss_pct > 3.0
    return {"session_id": session_id, "degraded": degraded}


@app.post("/sessions/{session_id}/end")
async def end_session(session_id: str, request: SessionEndRequest) -> dict:
    _assert_doctor_or_patient(request.actor_role)
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    session.status = SessionStatus.ENDED
    session.ended_at = datetime.now(UTC)
    _release_video_node(session.selected_media_node)
    return session.model_dump(mode="json")


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session": session.model_dump(mode="json"),
        "chat_messages": chat_messages.get(session_id, []),
        "files": uploaded_files.get(session_id, []),
        "quality": quality_events.get(session_id, []),
    }


@app.get("/video/nodes")
async def list_video_nodes() -> dict:
    return {"nodes": video_nodes}


@app.post("/speech/protocol")
async def speech_protocol(request: SpeechProtocolRequest) -> dict:
    if not has_permission(request.actor_role, "consultation:write:assigned"):
        raise HTTPException(status_code=403, detail="Only doctor can create protocol from speech")
    return speech_to_protocol(request.transcript)


@app.post("/complaints/analyze")
async def complaints_analyze(request: ComplaintAnalysisRequest) -> dict:
    _assert_doctor_or_patient(request.actor_role)
    return analyze_complaint(request.patient_id, request.text).model_dump(mode="json")
