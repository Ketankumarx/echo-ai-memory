# ECHO — Personal AI Memory Assistant

> **Capture conversation notes, automatically extract structured memories, and recall facts with zero hallucinations.**

---

## 🌟 What is ECHO?

**ECHO** is a consent-based personal memory assistant designed to help you capture, organize, and recall critical conversation details, deadlines, decisions, and recommendations. 

Instead of searching through fragmented notes, voice recordings, or chat logs, ECHO:
1. Listens when you explicitly press record or allows quick text entry of spoken notes.
2. Uses speech-to-text (Groq / OpenAI Whisper) and an AI extraction engine to extract structured memory capsules.
3. Persists memories locally in an ACID-compliant SQLite database.
4. Provides a grounded question-answering assistant (Ask ECHO) that cites sources and refuses to hallucinate facts not found in memory.
5. Grounds memory recall with live web search via **SerpApi** whenever questions require current external details.

---

## 🚀 Key Features

- **🎙️ Explicit Consent Voice Capture**: Real browser microphone recording using the browser `MediaRecorder` API with live reactive waveform visualization, active `🔴 RECORDING` indicators, and automatic audio blob uploading.
- **📝 Instant Note Demo Path**: A robust text entry box that runs the exact same AI memory extraction and database pipeline without needing microphone permissions.
- **🧠 Atomic Memory Extraction**: Automatically identifies people, topics, action verbs, dates, deadlines, suggestions, and relevance scores.
- **💾 Local SQLite Storage**: Lightweight, reliable local persistence in `echo_memory.db` with structured metadata, categories, and tags.
- **🔎 Real-Time Memory Search**: Instant keyword search matching people, topics, tags, and facts, paired with category filtering chips (Deadlines, Suggestions, Work, Personal).
- **💬 Grounded Ask ECHO Recall**: Natural language querying with strict grounding. When asked about something not recorded (e.g. *"What did Rahul tell me about quantum computing?"*), ECHO clearly responds: *"I don't have a memory containing that information."*
- **📚 Interactive Source Citations**: Every memory-based answer cites the exact memories retrieved from your personal database.
- **🌐 SerpApi Live Web Grounding**: Seamlessly queries Google Search through SerpApi to supplement personal memories with up-to-date web information, presenting distinct citations and links.
- **🗑️ Real Memory Deletion**: One-click memory deletion removing items permanently from SQLite and immediately updating the UI.
- **🌐 Multilingual & Language Policy**:
  - **Memory Storage**: English input is stored in English (never converted to Hinglish). Hindi/mixed input is normalized into natural Roman Hinglish using Latin script only (never Devanagari script).
  - **Ask ECHO Input**: Users can query in English, Roman Hindi, or Hinglish (and Devanagari).
  - **ECHO Responses**: ECHO **ALWAYS responds in English** regardless of the query language.
- **🛡️ Privacy-First Design**: Microphone access occurs *only* when the user explicitly clicks record. No secret or passive background listening.

---

## 🏛️ Architecture Flow

```
USER
  │
  ├── 🎙️ Browser Microphone (MediaRecorder API) ──> Audio Blob (WebM)
  │                                                      │
  └── 📝 Manual Text Note ("Rahul told me...")          │
                                                         ▼
                                             POST /api/audio/ingest
                                                         │
                                             📝 Speech-to-Text (Groq/OpenAI Whisper)
                                                         │
                                                         ▼
                                             🧠 Memory Extraction Engine (Gemini/OpenAI/Heuristic)
                                                         │
                                                         ▼
                                             💾 SQLite Database (echo_memory.db)
                                                         │
                                       ┌─────────────────┴─────────────────┐
                                       ▼                                   ▼
                              GET /api/memories                 POST /api/memories/query
                               (Feed & Search)                       (Ask ECHO Recall)
                                                                           │
                                                               🔎 Semantic Memory Retrieval
                                                                           │
                                                               🌐 SerpApi Live Search (Optional)
                                                                           │
                                                               🤖 Strictly Grounded Answer
                                                                           │
                                                               📚 Source Citations & Web Links
```

---

## 💻 Tech Stack

### Frontend
- **Framework**: React 18 with Vite
- **Styling**: Vanilla CSS design system with custom CSS variables, glassmorphism, responsive 2-column grid, and dark theme
- **Icons**: Custom SVG icons (`MicIcon`, `BrainIcon`, `SparklesIcon`, `ExternalLinkIcon`, `ShieldCheckIcon`)
- **Audio APIs**: Browser `MediaRecorder` API and Web Audio `AudioContext` / `AnalyserNode`

### Backend
- **Framework**: FastAPI (Python 3.10+) with Uvicorn ASGI server
- **Database**: SQLite3 (`echo_memory.db`) with tables: `memories`, `audio_sessions`, `chat_queries`
- **Speech-to-Text (STT)**: Groq Whisper (`whisper-large-v3`) or OpenAI Whisper (`whisper-1`)
- **AI Extraction & Grounding**: Google Gemini (`gemini-2.0-flash` / `gemini-1.5-flash`), OpenAI (`gpt-4o-mini`), or built-in offline heuristic engine
- **Web Grounding**: Google Search via SerpApi (`https://serpapi.com`)

---

## ⚙️ Environment Variables

Create a `.env` file in `backend/.env` (or copy from `.env.example`):

```bash
# Speech-to-Text (Recommended: Groq for sub-second Whisper transcription)
GROQ_API_KEY=your_groq_api_key_here

# LLM & Embeddings (Gemini or OpenAI)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Web Grounding (Google Search API via SerpApi)
SERPAPI_API_KEY=your_serpapi_api_key_here

# Local Storage
DATABASE_PATH=echo_memory.db
AUDIO_UPLOAD_DIR=uploads/audio
```

> **Note**: ECHO operates in offline zero-setup demo mode if API keys are not yet configured. Manual text notes, memory extraction, SQLite persistence, memory search, deletion, and grounded memory recall work out of the box! When you add API keys, live Whisper transcription, Gemini/OpenAI reasoning, and SerpApi live web search activate automatically.

---

## 🚀 Getting Started

### 1. Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start FastAPI server on port 8000
PYTHONPATH=. uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend will be available at `http://127.0.0.1:8000` (Interactive Swagger docs at `http://127.0.0.1:8000/docs`).

### 2. Frontend Setup

```bash
cd frontend
npm install

# Start Vite dev server on port 5173
npm run dev -- --host 127.0.0.1 --port 5173
```

Frontend will be available at `http://127.0.0.1:5173`. Vite automatically proxies `/api` requests to the backend.

---

## 🧪 Testing the Application

### Automated End-to-End Test Suite

Run the full integration test script:

```bash
python3 -c "
import urllib.request, json
base = 'http://127.0.0.1:5173'
# 1. Health
print('Health:', json.loads(urllib.request.urlopen(base + '/api/health').read()))
# 2. Memories
mems = json.loads(urllib.request.urlopen(base + '/api/memories').read())
print(f'Memories in DB: {len(mems)}')
# 3. Query
req = urllib.request.Request(base + '/api/memories/query', data=json.dumps({'question': 'What did Rahul tell me about the hackathon?'}).encode(), headers={'Content-Type': 'application/json'})
print('Answer:', json.loads(urllib.request.urlopen(req).read())['answer'])
"
```

### Manual Frontend Validation

1. **Open** `http://127.0.0.1:5173` in your browser.
2. Observe the initial memories loaded from SQLite.
3. Test **Search memories**: type `"Rahul"` or `"Friday"` in the search bar.
4. Test **Filter chips**: click `"Deadlines"` to filter by category.
5. In **Ask ECHO**, click a prompt chip or ask:
   - *"What did Rahul tell me about the hackathon?"*
   - *"What technologies did he suggest?"*
   - *"What did Rahul tell me about quantum computing?"* (Notice: zero hallucinations!)
6. In **Quick Note Input**, enter:
   `"Rahul told me our hackathon submission is Friday at 5 PM and we should use React and Firebase."`
   Click **Add**. Watch the memory appear in the list immediately!
7. Click the **Trash** icon on a memory card to delete it from SQLite.

---

## 🌐 SerpApi Integration Details

SerpApi is integrated directly into ECHO's retrieval and synthesis pipeline:
- When a user asks a question about an external tool, company, or current topic (e.g., *"What is React 19 and what does it do?"* or *"What is Acme AI?"*):
  1. ECHO retrieves personal memories first.
  2. Queries SerpApi Google Search API for top organic results.
  3. Returns a combined response that clearly distinguishes **Personal Memory** from **Current Web Information**.
  4. Provides clickable source links to verify external information.
  5. If `SERPAPI_API_KEY` is not set, personal memory recall continues functioning and the user is informed that live web search is unconfigured.

---

## 🔒 Privacy & Security

- **Explicit User Consent**: Microphone hardware is accessed only upon explicit user interaction ("Start Recording"). Background recording is strictly disabled.
- **Server-Side API Keys**: All provider API keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `SERPAPI_API_KEY`) remain strictly on the backend.
- **Audio Validation**: Uploaded audio is validated for format, length, and size (< 25MB).
- **No Hallucinations**: Strict prompt and deterministic constraints ensure that memories are never invented.

---

## 🏆 Hackathon Demo Script

For judging and presentations, follow this exact sequence:

1. **Open ECHO** at `http://127.0.0.1:5173`.
2. **Add Spoken Note**:
   Paste into the note input:
   > *"Rahul told me our hackathon submission is Friday at 5 PM and we should use React and Firebase."*
   Click **Add**.
3. **Show Extracted Memory**:
   Show the new memory card with person (*Rahul*), topic (*Hackathon Submission*), tags (*#hackathon*, *#react*, *#firebase*), and deadline importance.
4. **Ask ECHO (Memory Recall)**:
   Ask: *"What did Rahul tell me about the hackathon?"*
   👉 ECHO answers: *"Rahul told you that the hackathon submission is Friday at 5 PM and suggested using React and Firebase."*
5. **Ask Follow-up**:
   Ask: *"What technologies did he suggest?"*
   👉 ECHO answers: *"React and Firebase."*
6. **Hallucination Prevention Check**:
   Ask: *"What did Rahul tell me about quantum computing?"*
   👉 ECHO answers: *"I don't have a memory containing that information."*
7. **Web Grounding (SerpApi)**:
   Ask: *"What is React 19?"*
   👉 ECHO grounds personal memory with live web search results and source badges.

---

## 🔮 Future Improvements

- Vector embeddings with ChromaDB / FAISS for fuzzy semantic vector similarity.
- Multi-user authentication and encrypted memory vaults.
- Mobile progressive web app (PWA) with native voice recording permissions.
