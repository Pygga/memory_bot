from sentence_transformers import SentenceTransformer

_model = None


def get_embedding(text: str) -> list[float]:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = _model.encode(text, normalize_embeddings=True)
    return embedding.tolist()
