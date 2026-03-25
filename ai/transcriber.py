import os
from groq import Groq

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def transcribe_audio(file_path: str) -> str:
    with open(file_path, "rb") as f:
        result = _client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3-turbo",
        )
    return result.text.strip()
