import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.core.config import settings

def get_connection():
    conn = sqlite3.connect(settings.DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def format_relative_time(iso_str: str) -> str:
    """Format ISO timestamp into human-readable relative time."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.utcnow()
        # If timezone aware, compare or strip
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        diff = now - dt
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            mins = int(seconds // 60)
            return f"{mins}m ago"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f"Today, {dt.strftime('%I:%M %p')}"
        elif seconds < 172800:
            return f"Yesterday, {dt.strftime('%I:%M %p')}"
        else:
            return dt.strftime("%b %d, %I:%M %p")
    except Exception:
        return "Recently"

def format_memory_row(r: Any) -> Dict[str, Any]:
    people = json.loads(r["people_mentioned"] or "[]")
    tags = json.loads(r["tags"] or "[]")
    subject = r["subject"] or (people[0] if people else "Note")
    obj = r["object"] or ""
    
    # Topic synthesis
    topic = obj if (obj and len(obj) < 40) else (f"{subject} Note" if subject else "General")
    if "coffee" in r["full_fact"].lower():
        topic = "Team Celebration"
    elif "demo" in r["full_fact"].lower() or "judging" in r["full_fact"].lower():
        topic = "Demo Strategy"
    elif "serpapi" in r["full_fact"].lower():
        topic = "SerpApi Integration"
    elif "visual" in r["full_fact"].lower() or "waveform" in r["full_fact"].lower():
        topic = "Audio Visuals"
    elif "hackathon" in r["full_fact"].lower() or "submission" in r["full_fact"].lower():
        topic = "Hackathon Submission"

    return {
        "id": r["id"],
        "session_id": r["session_id"],
        "subject": r["subject"],
        "predicate": r["predicate"],
        "object": r["object"],
        "full_fact": r["full_fact"],
        "category": r["category"] or "general",
        "people_mentioned": people,
        "tags": tags,
        "importance_score": r["importance_score"] or 3,
        "created_at": r["created_at"],
        # Frontend compatibility fields
        "person": subject,
        "topic": topic,
        "fact": r["full_fact"],
        "dateTime": format_relative_time(r["created_at"]),
        "importance": r["importance_score"] or 3
    }

format_memory_dict = format_memory_row

def init_db():

    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. audio_sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audio_sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        raw_transcript TEXT NOT NULL,
        audio_duration_seconds REAL DEFAULT 0.0,
        created_at TEXT NOT NULL
    );
    """)
    
    # 2. memories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        subject TEXT,
        predicate TEXT,
        object TEXT,
        full_fact TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        people_mentioned TEXT DEFAULT '[]',
        tags TEXT DEFAULT '[]',
        importance_score INTEGER DEFAULT 3,
        embedding TEXT DEFAULT '[]',
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES audio_sessions(id) ON DELETE SET NULL
    );
    """)
    
    # 3. chat_queries table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_queries (
        id TEXT PRIMARY KEY,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        retrieved_memory_ids TEXT DEFAULT '[]',
        web_sources TEXT DEFAULT '[]',
        search_query_used TEXT,
        created_at TEXT NOT NULL
    );
    """)
    
    conn.commit()

    # Check if memories table is empty; if so, seed initial default memories
    cursor.execute("SELECT count(*) as count FROM memories")
    count_row = cursor.fetchone()
    if count_row and count_row["count"] == 0:
        now = datetime.utcnow().isoformat()
        seeds = [
            (
                "mem-1", None, "Rahul", "informed", "hackathon submission is Friday at 5 PM using React and Firebase",
                "Rahul told me that our hackathon submission is Friday at 5 PM and we should use React and Firebase.",
                "deadline", json.dumps(["Rahul"]), json.dumps(["hackathon", "submission", "friday", "react", "firebase"]),
                5, json.dumps([]), now
            ),
            (
                "mem-2", None, "Priya", "mentioned", "judging criteria heavily weights live demo reliability and UI polish",
                "Priya mentioned that the judging criteria heavily weights live demo reliability, zero latency, and UI polish.",
                "suggestion", json.dumps(["Priya"]), json.dumps(["demo", "judging", "ui", "criteria"]),
                4, json.dumps([]), now
            ),
            (
                "mem-3", None, "Alex", "suggested", "integrating SerpApi so ECHO can ground personal memory with current web information",
                "Alex suggested integrating SerpApi so ECHO can seamlessly ground personal memory with current web information.",
                "work", json.dumps(["Alex"]), json.dumps(["serpapi", "web-search", "grounding"]),
                4, json.dumps([]), now
            ),
            (
                "mem-4", None, "Rahul", "emphasized", "having dynamic waveform visuals so users have immediate feedback when speaking",
                "Rahul emphasized having dynamic waveform visuals so users have immediate feedback when speaking.",
                "suggestion", json.dumps(["Rahul"]), json.dumps(["waveform", "visuals", "ux"]),
                3, json.dumps([]), now
            ),
            (
                "mem-5", None, "Sara", "recommended", "checking out Blue Bottle Coffee downtown for team coffee",
                "Sara recommended checking out the new Blue Bottle Coffee downtown for post-hackathon coffee.",
                "personal", json.dumps(["Sara"]), json.dumps(["coffee", "team", "downtown"]),
                2, json.dumps([]), now
            )
        ]
        cursor.executemany("""
        INSERT INTO memories (
            id, session_id, subject, predicate, object, full_fact, category,
            people_mentioned, tags, importance_score, embedding, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seeds)
        conn.commit()

    conn.close()

def create_audio_session(title: str, raw_transcript: str, duration: float = 0.0) -> str:
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audio_sessions (id, title, raw_transcript, audio_duration_seconds, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, title, raw_transcript, duration, now)
    )
    conn.commit()
    conn.close()
    return session_id

def insert_memory(
    full_fact: str,
    session_id: Optional[str] = None,
    subject: Optional[str] = None,
    predicate: Optional[str] = None,
    object: Optional[str] = None,
    category: str = "general",
    people_mentioned: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    importance_score: int = 3,
    embedding: Optional[List[float]] = None
) -> Dict[str, Any]:
    memory_id = f"mem-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()
    people_json = json.dumps(people_mentioned or [])
    tags_json = json.dumps(tags or [])
    embedding_json = json.dumps(embedding or [])
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO memories (
            id, session_id, subject, predicate, object, full_fact, category,
            people_mentioned, tags, importance_score, embedding, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            memory_id, session_id, subject, predicate, object, full_fact, category,
            people_json, tags_json, importance_score, embedding_json, now
        )
    )
    conn.commit()
    
    cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
    row = cursor.fetchone()
    conn.close()
    
    return format_memory_row(row)

def get_memories(
    category: Optional[str] = None,
    search: Optional[str] = None,
    person: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM memories WHERE 1=1"
    params = []
    
    if category and category.lower() != "all":
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category)
        
    if search:
        search_pattern = f"%{search.strip()}%"
        query += """ AND (
            full_fact LIKE ? OR 
            tags LIKE ? OR 
            subject LIKE ? OR 
            object LIKE ? OR 
            people_mentioned LIKE ?
        )"""
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
        
    if person:
        person_pattern = f"%{person.strip()}%"
        query += " AND (people_mentioned LIKE ? OR subject LIKE ?)"
        params.extend([person_pattern, person_pattern])
        
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [format_memory_row(r) for r in rows]

def get_memory_by_id(memory_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
    row = cursor.fetchone()
    conn.close()
    return format_memory_row(row) if row else None

def delete_memory(memory_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def search_memories_for_query(query_text: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search memories relevant to natural language question.
    Supports English, Roman Hindi / Hinglish, and Devanagari Hindi questions.
    Extracts keywords, entity names, and scores memories based on match relevance.
    """
    if not query_text or not query_text.strip():
        return []

    # If query is in Devanagari, transliterate to Roman Hinglish for search
    from app.services.language_service import has_devanagari, rule_based_devanagari_to_hinglish
    if has_devanagari(query_text):
        query_text = rule_based_devanagari_to_hinglish(query_text)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memories")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    # Stopwords in English and Hindi/Hinglish
    stopwords = {
        "what", "did", "tell", "me", "about", "the", "a", "an", "is", "was",
        "were", "are", "he", "she", "they", "we", "our", "my", "your", "to",
        "and", "or", "in", "on", "at", "for", "with", "how", "when", "why",
        "which", "who", "do", "does", "say", "saying", "tell", "mention",
        # Hindi & Hinglish stopwords
        "ke", "ki", "ka", "ko", "se", "mein", "par", "tha", "thi", "the",
        "hai", "hain", "kya", "kyun", "kaun", "kaha", "kare", "karna", "baare",
        "batao", "bataya", "bola", "bolo", "bhi", "toh", "kuch", "ne", "mujhe",
        "humko", "humein", "unhone", "usne", "kisi", "bare"
    }

    raw_tokens = [w.strip("?,.!;:\"'()[]{}").lower() for w in query_text.split()]
    tokens = [t for t in raw_tokens if t and t not in stopwords and len(t) > 1]
    
    # Extract known person names from rows
    person_names = set()
    for r in rows:
        people = json.loads(r["people_mentioned"] or "[]")
        for p in people:
            if p: person_names.add(p.lower())
        if r["subject"]:
            person_names.add(r["subject"].lower())

    topic_tokens = [t for t in tokens if t not in person_names]

    scored_memories = []
    lower_query = query_text.lower()

    # Intent detection across languages
    is_asking_suggestion = any(k in lower_query for k in ["suggest", "recommend", "sujhav", "sujhaav", "idea", "tech", "technology", "stack"])
    is_asking_deadline = any(k in lower_query for k in ["deadline", "when", "kab", "time", "submission", "friday", "shukrawar", "shukravaar", "date", "tarikh"])

    for r in rows:
        mem = format_memory_row(r)
        fact_lower = mem["full_fact"].lower()
        subject_lower = (mem["subject"] or "").lower()
        people_lower = [p.lower() for p in mem["people_mentioned"]]
        tags_lower = [t.lower() for t in mem["tags"]]
        category_lower = mem["category"].lower()

        score = 0
        person_matched = False

        # Exact subject/person match
        for p in people_lower:
            if p and p in lower_query:
                score += 10
                person_matched = True
        if subject_lower and subject_lower in lower_query:
            score += 8
            person_matched = True

        topic_matched = False

        # Keyword match in tags or fact
        for t in topic_tokens:
            if t in tags_lower:
                score += 6
                topic_matched = True
            if t in fact_lower:
                score += 4
                topic_matched = True
            if t == category_lower:
                score += 3
                topic_matched = True
            # Cross-lingual term normalization
            if t in ["shukrawar", "shukravaar"] and ("friday" in fact_lower or "friday" in tags_lower):
                score += 6
                topic_matched = True

        # Bonus for intent terms
        if is_asking_deadline:
            if category_lower == "deadline" or "friday" in fact_lower or "5 pm" in fact_lower or "shukrawar" in fact_lower:
                score += 6
                topic_matched = True

        if is_asking_suggestion:
            if category_lower == "suggestion" or "react" in fact_lower or "firebase" in fact_lower or "suggest" in fact_lower:
                score += 6
                topic_matched = True

        # CRITICAL: If query specified topic tokens or intent, ensure topic alignment
        if topic_tokens and not topic_matched:
            continue

        if score > 0:
            scored_memories.append((score, mem))

    # Sort descending by score
    scored_memories.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_memories[:limit]]

search_relevant_memories = search_memories_for_query

def save_chat_query(

    question: str,
    answer: str,
    retrieved_memory_ids: List[str],
    web_sources: List[Dict[str, Any]],
    search_query_used: Optional[str] = None
) -> str:
    query_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO chat_queries (id, question, answer, retrieved_memory_ids, web_sources, search_query_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (query_id, question, answer, json.dumps(retrieved_memory_ids), json.dumps(web_sources), search_query_used, now)
    )
    conn.commit()
    conn.close()
    return query_id
