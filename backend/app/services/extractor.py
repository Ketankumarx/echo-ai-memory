import json
import re
import httpx
from typing import List
from app.core.config import settings
from app.models.schemas import ExtractedMemoryItem
from app.services.language_service import normalize_text_for_storage, has_devanagari

EXTRACTION_SYSTEM_PROMPT = """You are ECHO's Memory Extraction Engine.
Analyze the user's conversation transcript or note.
Extract distinct, atomic, structured memories.
Each memory must be self-contained and clear without ambiguity.
Do NOT invent information. If something is not present, do not create it.

LANGUAGE POLICY (CRITICAL):
- If the text is English -> extract and store the memory in English.
- If the text is Hindi or Hinglish -> convert and store as natural Roman Hinglish using Latin script only.
- NEVER output Devanagari script in any field (subject, predicate, object, full_fact, tags).
- Do NOT convert English text into Hinglish.

For each memory provide:
- subject: The key person, tool, or entity (e.g., "Rahul", "Team", "User")
- predicate: The action or relationship (e.g., "told", "recommended", "bataya", "deadline is")
- object: The detail, task, or recommendation (e.g., "hackathon Friday ko hai", "hackathon submission is Friday at 5 PM using React")
- full_fact: A complete, natural standalone sentence summarizing the memory in Latin script (e.g., "Rahul ne mujhe bataya ki hackathon Friday ko hai" or "Rahul told me the hackathon submission is Friday at 5 PM.")
- category: One of ["deadline", "suggestion", "personal", "work", "event", "general"]
- people_mentioned: List of people names mentioned (e.g., ["Rahul"])
- tags: Array of 2 to 5 relevant lowercase keywords (e.g., ["hackathon", "friday", "rahul"])
- importance_score: Integer from 1 to 5 (5 being critical like an imminent deadline, 3 being standard advice)

Return ONLY valid JSON with this format:
{
  "memories": [ ... ]
}
"""

async def extract_memories_from_text(text: str) -> List[ExtractedMemoryItem]:
    """
    Extracts structured memory capsules from transcript text using Groq, Gemini, or OpenAI,
    with an intelligent rule-based fallback if no LLM key is present.
    Ensures memory text is normalized (English -> English, Hindi/Hinglish -> Roman Hinglish, NO Devanagari).
    """
    text = text.strip()
    if not text:
        return []

    # 1. Normalize text upfront according to ECHO's language policy (never Devanagari)
    normalized_text = await normalize_text_for_storage(text)

    # 2. Try Groq (ultra-fast using already-configured GROQ_API_KEY)
    if settings.GROQ_API_KEY:
        for model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Extract memories from this text:\n\n{normalized_text}"}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
                headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
                async with httpx.AsyncClient(timeout=15.0) as client:
                    res = await client.post(url, json=payload, headers=headers)
                    if res.status_code == 200:
                        data = res.json()
                        content_text = data["choices"][0]["message"]["content"]
                        parsed = json.loads(content_text)
                        items = parsed.get("memories", [])
                        if items:
                            validated = []
                            for item in items:
                                # Ensure no Devanagari characters leaked
                                for k in ["subject", "predicate", "object", "full_fact"]:
                                    if item.get(k) and has_devanagari(item[k]):
                                        item[k] = await normalize_text_for_storage(item[k])
                                validated.append(ExtractedMemoryItem(**item))
                            return validated
            except Exception as e:
                print(f"[Extractor] Groq extraction on {model} failed: {e}")

    # 3. Try Gemini if GEMINI_API_KEY is configured
    if settings.GEMINI_API_KEY:
        for model in ["gemini-2.0-flash", "gemini-1.5-flash"]:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": EXTRACTION_SYSTEM_PROMPT},
                                {"text": f"Extract memories from this text:\n\n{normalized_text}"}
                            ]
                        }
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1
                    }
                }
                async with httpx.AsyncClient(timeout=20.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        content_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(content_text)
                        items = parsed.get("memories", [])
                        if items:
                            return [ExtractedMemoryItem(**item) for item in items]
            except Exception as e:
                print(f"[Extractor] Gemini extraction failed on {model}: {e}")

    # 4. Try OpenAI if OPENAI_API_KEY is configured
    if settings.OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Extract memories from this text:\n\n{normalized_text}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    content_text = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content_text)
                    items = parsed.get("memories", [])
                    if items:
                        return [ExtractedMemoryItem(**item) for item in items]
        except Exception as e:
            print(f"[Extractor] OpenAI extraction failed: {e}")

    # 5. Intelligent Heuristic Fallback
    return _heuristic_memory_extraction(normalized_text)

def _heuristic_memory_extraction(text: str) -> List[ExtractedMemoryItem]:
    """Smart heuristic parsing for offline/no-key hackathon demos supporting English and Hinglish."""
    items = []
    lower_text = text.lower()
    
    # 1. Detect person names
    known_names = ["Rahul", "Priya", "Alex", "Sam", "Sara", "John", "David", "Alice", "Bob", "Ketan"]
    people = []
    for name in known_names:
        if re.search(rf"\b{name}\b", text, re.IGNORECASE):
            people.append(name)
            
    # Check "Name told/said/ne bataya/ne bola"
    name_match = re.match(r"^([A-Z][a-z]+)\s+(?:told|said|suggested|mentioned|shared|informed|ne\s+bataya|ne\s+kaha|ne\s+bola)", text)
    if name_match:
        matched_name = name_match.group(1)
        if matched_name not in people:
            people.insert(0, matched_name)
            
    subject = people[0] if people else "User Note"

    # 2. Category detection (English & Hinglish)
    is_deadline = any(k in lower_text for k in [
        "deadline", "due", "friday", "shukrawar", "pm", "am", "submission",
        "schedule", "tomorrow", "clock", "ko hai", "baje", "tarikh", "shaam"
    ])
    is_suggestion = any(k in lower_text for k in [
        "suggest", "recommend", "should", "idea", "use", "try", "stack",
        "suggest kiya", "karna chahiye", "bola tha", "use karein"
    ])
    is_work = any(k in lower_text for k in ["work", "project", "hackathon", "build", "code", "api", "database"])
    is_personal = any(k in lower_text for k in ["coffee", "chai", "lunch", "dinner", "birthday", "friend", "home"])

    if is_deadline:
        category = "deadline"
    elif is_suggestion:
        category = "suggestion"
    elif is_work:
        category = "work"
    elif is_personal:
        category = "personal"
    else:
        category = "general"

    # 3. Tags extraction
    tags = []
    potential_tags = [
        "hackathon", "submission", "friday", "deadline", "react", "firebase",
        "serpapi", "fastapi", "python", "sqlite", "ui", "demo", "judging",
        "coffee", "team", "meeting", "presentation"
    ]
    for tag in potential_tags:
        if tag in lower_text and tag not in tags:
            tags.append(tag)

    if people and people[0].lower() not in tags:
        tags.insert(0, people[0].lower())

    if not tags:
        tags = ["echo", category]

    # 4. Synthesize object / topic
    topic = "Note"
    if "hackathon" in lower_text:
        topic = "Hackathon Submission"
    elif "serpapi" in lower_text:
        topic = "SerpApi Grounding"
    elif "react" in lower_text or "firebase" in lower_text:
        topic = "Tech Stack Recommendation"
    elif is_deadline:
        topic = "Upcoming Deadline"
    elif is_suggestion:
        topic = "Suggestion"
    elif people:
        topic = f"{people[0]} Conversation"

    importance = 5 if is_deadline else (4 if is_suggestion or is_work else 3)

    items.append(
        ExtractedMemoryItem(
            subject=subject,
            predicate="conveyed" if people else "recorded",
            object=topic,
            full_fact=text,
            category=category,
            people_mentioned=people,
            tags=tags[:5],
            importance_score=importance
        )
    )
    return items
