from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ExtractedMemoryItem(BaseModel):
    subject: Optional[str] = Field(None, description="Primary person, object, or entity (e.g. Rahul)")
    predicate: Optional[str] = Field(None, description="Action or relation (e.g. told, recommended, scheduled)")
    object: Optional[str] = Field(None, description="Target or details (e.g. hackathon submission is Friday 5 PM)")
    full_fact: str = Field(..., description="Complete stand-alone factual memory sentence")
    category: str = Field("general", description="Category: deadline, suggestion, personal, work, event, general")
    people_mentioned: List[str] = Field(default_factory=list, description="List of people referenced")
    tags: List[str] = Field(default_factory=list, description="Key search tags")
    importance_score: int = Field(3, ge=1, le=5, description="Importance rating 1 to 5")

class MemoryResponse(BaseModel):
    id: str
    session_id: Optional[str] = None
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object: Optional[str] = None
    full_fact: str
    category: str = "general"
    people_mentioned: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    importance_score: int = 3
    created_at: str
    
    # Frontend compatibility fields
    person: Optional[str] = None
    topic: Optional[str] = None
    fact: Optional[str] = None
    dateTime: Optional[str] = None
    importance: Optional[int] = None

class ManualMemoryCreate(BaseModel):
    text: str = Field(..., min_length=2, description="Raw statement or note to convert into memory")

class AudioIngestResponse(BaseModel):
    session_id: str
    transcript: str
    audio_duration_seconds: float = 0.0
    memories: List[MemoryResponse] = Field(default_factory=list)
    message: str

class WebSource(BaseModel):
    title: str
    link: str
    snippet: str
    source_engine: str = "Google (SerpApi)"

class ChatQueryRequest(BaseModel):
    query: Optional[str] = Field(None, description="Natural language question to ask ECHO")
    question: Optional[str] = Field(None, description="Alternative field for question")
    enable_web_grounding: bool = Field(True, description="Allow SerpApi search when applicable")

class ChatQueryResponse(BaseModel):
    answer: str
    memories_referenced: List[MemoryResponse] = Field(default_factory=list)
    web_grounded: bool = False
    web_search_query: Optional[str] = None
    web_sources: List[WebSource] = Field(default_factory=list)
    created_at: str

class HealthStatus(BaseModel):
    status: str
    database: str
    configured_keys: dict
    timestamp: str
