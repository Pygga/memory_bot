import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from db.models import Entry


def _embeddings_matrix(entries: list[Entry]) -> np.ndarray:
    return np.array([e.embedding for e in entries], dtype=np.float32)


def cluster_entries(
    entries: list[Entry],
    n_clusters: int | None = None,
    max_clusters: int = 8,
) -> tuple[list[int], int]:
    """Кластеризует записи K-means по эмбеддингам.

    Если n_clusters не задан — подбирает оптимальное число кластеров
    по silhouette score (от 2 до max_clusters).

    Возвращает: (список меток кластеров, итоговое число кластеров)
    """
    X = _embeddings_matrix(entries)

    if n_clusters is None:
        best_k, best_score = 2, -1
        upper = min(max_clusters, len(entries) - 1)
        for k in range(2, upper + 1):
            km = KMeans(n_clusters=k, random_state=42, n_init="auto")
            labels = km.fit_predict(X)
            score = silhouette_score(X, labels)
            if score > best_score:
                best_score, best_k = score, k
        n_clusters = best_k

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = km.fit_predict(X).tolist()
    return labels, n_clusters


def reduce_to_2d(entries: list[Entry]) -> np.ndarray:
    """Снижает размерность эмбеддингов до 2D через PCA (для визуализации)."""
    X = _embeddings_matrix(entries)
    pca = PCA(n_components=2, random_state=42)
    return pca.fit_transform(X)


def get_cluster_samples(
    entries: list[Entry],
    labels: list[int],
    n_clusters: int,
    samples_per_cluster: int = 3,
) -> dict[int, list[Entry]]:
    """Возвращает несколько представительных записей для каждого кластера."""
    clusters: dict[int, list[Entry]] = {i: [] for i in range(n_clusters)}
    for entry, label in zip(entries, labels):
        if len(clusters[label]) < samples_per_cluster:
            clusters[label].append(entry)
    return clusters
