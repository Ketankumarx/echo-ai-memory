import os
import uuid
import aiofiles
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import (
    init_db,
    get_memories,
    insert_memory,
    delete_memory,
    create_audio_session
)
from app.models.schemas import (
    HealthStatus,
    MemoryResponse,
    ManualMemoryCreate,
    AudioIngestResponse,
    ChatQueryRequest,
    ChatQueryResponse
)
from app.services.stt_service import transcribe_audio_file
from app.services.extractor import extract_memories_from_text
from app.services.query_service import execute_echo_query
from app.services.language_service import (
    has_devanagari,
    rule_based_devanagari_to_hinglish,
    normalize_text_for_storage
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed defaults on startup
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="ECHO: Personal AI Memory Assistant backend API with grounded memory retrieval and multilingual support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {
        "app": settings.PROJECT_NAME,
        "status": "online",
        "docs_url": "/docs",
        "language_policy": {
            "storage": "English stays English. Hindi/Hinglish converted to Roman Hinglish. Never Devanagari.",
            "input": "Accepts English, Roman Hindi, and Hinglish.",
            "response": "ECHO always responds in English."
        },
        "api_endpoints": {
            "health": "/api/health",
            "memories": "/api/memories",
            "manual_ingest": "/api/memories/manual",
            "audio_ingest": "/api/audio/ingest",
            "query": "/api/memories/query",
            "delete_memory": "/api/memories/{id}"
        }
    }

@app.get("/api/health", response_model=HealthStatus)
def health_check():
    return HealthStatus(
        status="healthy",
        database="connected (sqlite)",
        configured_keys={
            "GEMINI_API_KEY": bool(settings.GEMINI_API_KEY),
            "OPENAI_API_KEY": bool(settings.OPENAI_API_KEY),
            "GROQ_API_KEY": bool(settings.GROQ_API_KEY),
            "SERPAPI_API_KEY": bool(settings.SERPAPI_API_KEY),
        },
        timestamp=datetime.utcnow().isoformat()
    )

# -------------------------------------------------------------------------
# MEMORIES CRUD & RETRIEVAL
# -------------------------------------------------------------------------

@app.get("/api/memories", response_model=List[MemoryResponse])
def list_memories(
    category: Optional[str] = Query(None, description="Category filter (deadline, suggestion, work, personal, all)"),
    search: Optional[str] = Query(None, description="Search term for full text and tags (English or Hindi/Hinglish)"),
    person: Optional[str] = Query(None, description="Filter by person name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Retrieve personal memories with optional search and category filters."""
    # If search term has Devanagari, convert to Roman Hinglish for matching
    search_term = search
    if search_term and has_devanagari(search_term):
        search_term = rule_based_devanagari_to_hinglish(search_term)

    memories = get_memories(category=category, search=search_term, person=person, limit=limit, offset=offset)
    return [MemoryResponse(**m) for m in memories]

@app.post("/api/memories/manual", response_model=List[MemoryResponse])
@app.post("/api/memories/create", response_model=List[MemoryResponse])
async def create_manual_memory(payload: ManualMemoryCreate):
    """
    Ingest a manual note / spoken transcript directly.
    Language Policy:
    - English stays in English.
    - Hindi / Hinglish is converted to natural Roman Hinglish (never Devanagari).
    """
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    # 1. Normalize text according to language policy (never Devanagari in storage)
    normalized_text = await normalize_text_for_storage(text)

    # 2. Create a session record for tracking
    session_id = create_audio_session(
        title=f"Note: {normalized_text[:30]}...",
        raw_transcript=normalized_text,
        duration=0.0
    )

    # 3. Extract structured memories
    extracted_items = await extract_memories_from_text(normalized_text)
    if not extracted_items:
        raise HTTPException(status_code=422, detail="Could not extract any structured memories from provided text.")

    # 4. Save each memory to SQLite
    saved_memories = []
    for item in extracted_items:
        mem_dict = insert_memory(
            session_id=session_id,
            subject=item.subject,
            predicate=item.predicate,
            object=item.object,
            full_fact=item.full_fact,
            category=item.category,
            people_mentioned=item.people_mentioned,
            tags=item.tags,
            importance_score=item.importance_score
        )
        saved_memories.append(MemoryResponse(**mem_dict))

    return saved_memories

@app.delete("/api/memories/{memory_id}")
def delete_single_memory(memory_id: str):
    """Permanently delete a memory by ID."""
    success = delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Memory with ID '{memory_id}' not found.")
    return {"success": True, "id": memory_id, "message": "Memory deleted successfully."}

# -------------------------------------------------------------------------
# AUDIO INGEST & TRANSCRIPTION
# -------------------------------------------------------------------------

@app.post("/api/audio/ingest", response_model=AudioIngestResponse)
async def ingest_audio_stream(
    file: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None)
):
    """
    Accepts recorded audio Blob, verifies format, executes STT via Groq/OpenAI,
    normalizes script (Devanagari -> Roman Hinglish, English -> English),
    extracts structured memories, and persists to SQLite.
    """
    upload = file or audio
    if not upload:
        raise HTTPException(status_code=400, detail="No audio file was uploaded in request (expected 'file' or 'audio').")

    # Generate unique filename
    ext = os.path.splitext(upload.filename or "")[1] or ".webm"
    temp_filename = f"rec_{uuid.uuid4().hex[:10]}{ext}"
    temp_path = os.path.join(settings.AUDIO_UPLOAD_DIR, temp_filename)

    try:
        # Save file to disk
        async with aiofiles.open(temp_path, "wb") as out_file:
            content = await upload.read()
            if len(content) < 100:
                raise HTTPException(status_code=400, detail="Uploaded audio file is empty or too short.")
            await out_file.write(content)

        # Transcribe audio file
        try:
            transcript = await transcribe_audio_file(temp_path, filename=temp_filename)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

        if not transcript:
            raise HTTPException(status_code=422, detail="No speech could be detected in the uploaded audio.")

        # Normalize transcript according to language policy (never Devanagari in storage)
        normalized_transcript = await normalize_text_for_storage(transcript)

        # Estimate duration
        duration_est = max(1.0, round(len(content) / 16000.0, 1))

        # Create session
        session_id = create_audio_session(
            title=f"Voice Note ({datetime.utcnow().strftime('%b %d, %H:%M')})",
            raw_transcript=normalized_transcript,
            duration=duration_est
        )

        # Extract memories
        extracted_items = await extract_memories_from_text(normalized_transcript)
        saved_memories = []
        for item in extracted_items:
            mem_dict = insert_memory(
                session_id=session_id,
                subject=item.subject,
                predicate=item.predicate,
                object=item.object,
                full_fact=item.full_fact,
                category=item.category,
                people_mentioned=item.people_mentioned,
                tags=item.tags,
                importance_score=item.importance_score
            )
            saved_memories.append(MemoryResponse(**mem_dict))

        return AudioIngestResponse(
            session_id=session_id,
            transcript=normalized_transcript,
            audio_duration_seconds=duration_est,
            memories=saved_memories,
            message=f"Audio processed successfully. Extracted {len(saved_memories)} memory capsule(s)."
        )

    finally:
        pass

# -------------------------------------------------------------------------
# ASK ECHO (GROUNDED RECALL + SERPAPI)
# -------------------------------------------------------------------------

@app.post("/api/memories/query", response_model=ChatQueryResponse)
async def query_echo_memories(payload: ChatQueryRequest):
    """
    Ask ECHO: Performs grounded semantic recall from personal memory database.
    Language Policy:
    - Accepts questions in English, Roman Hindi, or Hinglish.
    - Always generates answers STRICTLY IN ENGLISH.
    - Zero hallucinations.
    """
    question = payload.query or payload.question
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question or query string is required.")

    response = await execute_echo_query(
        question=question,
        enable_web_grounding=payload.enable_web_grounding
    )
    return response
