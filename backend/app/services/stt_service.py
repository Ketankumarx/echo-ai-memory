import os
import httpx
from typing import Optional
from app.core.config import settings

async def transcribe_audio_file(file_path: str, filename: str = "audio.webm") -> str:
    """
    Transcribes an audio file using Groq Whisper (ultra-fast) or OpenAI Whisper.
    Raises ValueError if no STT provider key is configured or RuntimeError if transcription fails.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found at: {file_path}")

    # Check file size (e.g. limit to 25MB)
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > 25:
        raise ValueError(f"Audio file size ({file_size_mb:.1f} MB) exceeds maximum allowed size (25 MB).")

    # 1. Try Groq Whisper (primary/recommended)
    if settings.GROQ_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(file_path, "rb") as f:
                    # Provide appropriate content-type based on extension
                    mime = "audio/webm"
                    if filename.endswith(".wav"):
                        mime = "audio/wav"
                    elif filename.endswith(".mp4") or filename.endswith(".m4a"):
                        mime = "audio/mp4"
                    elif filename.endswith(".mp3"):
                        mime = "audio/mpeg"

                    files = {"file": (filename, f, mime)}
                    data = {
                        "model": "whisper-large-v3",
                        "response_format": "json",
                        "temperature": "0.0"
                    }
                    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
                    response = await client.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=headers
                    )
                    if response.status_code == 200:
                        result = response.json()
                        transcript = result.get("text", "").strip()
                        if transcript:
                            return transcript
                    else:
                        err_text = ""
                        try:
                            err_json = response.json()
                            err_text = err_json.get("error", {}).get("message", "")
                        except Exception:
                            pass
                        err_msg = err_text or f"HTTP {response.status_code}"
                        raise RuntimeError(f"Groq STT failed: {err_msg}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Groq connection failed: {str(e)}")

    # 2. Try OpenAI Whisper (fallback)
    if settings.OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(file_path, "rb") as f:
                    mime = "audio/webm"
                    if filename.endswith(".wav"):
                        mime = "audio/wav"
                    elif filename.endswith(".mp4") or filename.endswith(".m4a"):
                        mime = "audio/mp4"

                    files = {"file": (filename, f, mime)}
                    data = {"model": "whisper-1"}
                    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        files=files,
                        data=data,
                        headers=headers
                    )
                    if response.status_code == 200:
                        result = response.json()
                        transcript = result.get("text", "").strip()
                        if transcript:
                            return transcript
                    else:
                        err_text = ""
                        try:
                            err_json = response.json()
                            err_text = err_json.get("error", {}).get("message", "")
                        except Exception:
                            pass
                        err_msg = err_text or f"HTTP {response.status_code}"
                        raise RuntimeError(f"OpenAI STT failed: {err_msg}")
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"OpenAI connection failed: {str(e)}")

    # 3. If no key is configured
    raise ValueError(
        "Speech-to-text requires GROQ_API_KEY or OPENAI_API_KEY in backend/.env. "
        "For instant zero-setup demo testing, please use the text note input field below."
    )
