import re
import httpx
from typing import Optional
from app.core.config import settings

# Mapping for common Hindi/Devanagari words to natural Hinglish
COMMON_DEVANAGARI_WORDS = {
    "राहुल": "Rahul",
    "प्रिया": "Priya",
    "एलेक्स": "Alex",
    "सारा": "Sara",
    "ने": "ne",
    "मुझे": "mujhe",
    "बताया": "bataya",
    "कि": "ki",
    "हैकाथॉन": "hackathon",
    "हैकथॉन": "hackathon",
    "शुक्रवार": "Friday",
    "को": "ko",
    "है": "hai",
    "शाम": "shaam",
    "बजे": "baje",
    "सुझाव": "suggestion",
    "सुझाया": "suggest kiya",
    "दिया": "diya",
    "कहा": "kaha",
    "बोला": "bola",
    "प्रोजेक्ट": "project",
    "सबमिशन": "submission",
    "डेडलाइन": "deadline",
    "के": "ke",
    "बारे": "baare",
    "में": "mein",
    "क्या": "kya",
    "था": "tha",
    "थी": "thi",
    "कहा": "kaha",
}

# Devanagari character transliteration table
DEVANAGARI_MAP = {
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
    'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au',
    'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
    'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
    '्': '', 'ं': 'n', 'ँ': 'n', 'ः': 'h', '़': '',
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    '।': '.', '॥': '.'
}

def has_devanagari(text: str) -> bool:
    """Check if string contains any Devanagari Unicode characters."""
    return bool(re.search(r"[\u0900-\u097F]", text))

async def devanagari_to_roman_hinglish(text: str) -> str:
    """
    Converts Devanagari text into natural Roman Hinglish using Groq LLM (or Gemini/OpenAI),
    with an accurate rule-based phonetic fallback.
    """
    if not has_devanagari(text):
        return text

    # 1. Try Groq with qwen/qwen3.8-27b or openai/gpt-oss-120b
    if settings.GROQ_API_KEY:
        for model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
                payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a transliterator and Hindi-to-Hinglish converter. "
                                "Convert the user's Devanagari Hindi text into natural Roman Hinglish using Latin characters only. "
                                "Common loanwords like hackathon, Friday, submission, React, Firebase should use standard English spelling. "
                                "NEVER output Devanagari characters. "
                                "Return ONLY the converted Roman Hinglish text, without quotes or explanations."
                            )
                        },
                        {"role": "user", "content": text}
                    ],
                    "temperature": 0.1
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        converted = resp.json()["choices"][0]["message"]["content"].strip()
                        # Verify converted output does not have Devanagari
                        if converted and not has_devanagari(converted):
                            return converted
            except Exception as e:
                print(f"[LanguageService] Groq transliteration failed on {model}: {e}")

    # 2. Try Gemini if configured
    if settings.GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [{
                    "parts": [{"text": f"Convert this Devanagari Hindi text into natural Roman Hinglish using Latin script only. Do not output Devanagari: {text}"}]
                }],
                "generationConfig": {"temperature": 0.1}
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    converted = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if converted and not has_devanagari(converted):
                        return converted
        except Exception as e:
            print(f"[LanguageService] Gemini transliteration failed: {e}")

    # 3. Rule-based phonetic transliteration fallback
    return rule_based_devanagari_to_hinglish(text)

def rule_based_devanagari_to_hinglish(text: str) -> str:
    """Phonetic dictionary and character-level transliterator fallback."""
    # First, replace known words
    words = text.split()
    processed_words = []
    
    for w in words:
        clean_w = w.strip(".,!?()[]{}\"'")
        if clean_w in COMMON_DEVANAGARI_WORDS:
            replacement = COMMON_DEVANAGARI_WORDS[clean_w]
            w = w.replace(clean_w, replacement)
            processed_words.append(w)
        else:
            # Character-by-character transliterate
            w_out = []
            chars = list(w)
            i = 0
            while i < len(chars):
                ch = chars[i]
                if ch in DEVANAGARI_MAP:
                    mapped = DEVANAGARI_MAP[ch]
                    # In Devanagari, a standalone consonant has an inherent 'a' sound unless followed by halant or matra
                    if '\u0915' <= ch <= '\u0939':
                        next_ch = chars[i+1] if i + 1 < len(chars) else None
                        if next_ch and next_ch in ['ा', 'ि', 'ी', 'ु', 'ू', 'ृ', 'े', 'ै', 'ो', 'ौ', '्']:
                            w_out.append(mapped)
                        else:
                            w_out.append(mapped + ('a' if next_ch and '\u0915' <= next_ch <= '\u0939' else ''))
                    else:
                        w_out.append(mapped)
                else:
                    w_out.append(ch)
                i += 1
            processed_words.append("".join(w_out))

    result = " ".join(processed_words)
    # Strip any remaining Devanagari characters just in case
    result = re.sub(r"[\u0900-\u097F]", "", result).strip()
    return re.sub(r"\s+", " ", result)

async def normalize_text_for_storage(text: str) -> str:
    """
    Policy:
    1. If English -> store as English.
    2. If Hindi (Devanagari) -> convert to natural Roman Hinglish and store as Roman Hinglish.
    3. If mixed Hindi + English / Roman Hinglish -> store as natural Roman Hinglish.
    4. NEVER store Devanagari script.
    5. Do NOT convert English memories into Hinglish.
    """
    clean_text = text.strip()
    if not clean_text:
        return ""

    if has_devanagari(clean_text):
        return await devanagari_to_roman_hinglish(clean_text)

    # Pure English or Roman Hinglish: keep as is!
    return clean_text

async def normalize_question_for_search(question: str) -> str:
    """Normalizes question so that Devanagari is converted to Roman Hinglish for search."""
    if has_devanagari(question):
        return await devanagari_to_roman_hinglish(question)
    return question
