import whisper as _whisper

_model = None


def transcribe_audio(file_path: str) -> str:
    global _model
    if _model is None:
        _model = _whisper.load_model("base")
    result = _model.transcribe(file_path)
    return result["text"].strip()
