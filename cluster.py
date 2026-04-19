from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

def cluster_complaints(complaints: list[dict]) -> list[dict]:
    """
    Cluster similar complaints using TF-IDF + KMeans.
    Returns sorted list of clusters with label, count, and example quotes.
    """
    if not complaints:
        return []

    # Extract pain points for clustering
    pain_points = [c.get("pain_point", c["text"])[:300] for c in complaints]

    # ── Decide number of clusters based on data size ──────────────────────────
    n = len(pain_points)
    if n < 5:
        # Too few to cluster — return each as its own cluster
        return [
            {
                "label": c.get("pain_point", c["text"])[:60],
                "count": 1,
                "quotes": [c["text"][:300]],
                "score": 1
            }
            for c in complaints
        ]

    n_clusters = min(max(3, n // 5), 10)  # between 3 and 10 clusters

    # ── TF-IDF Vectorization ──────────────────────────────────────────────────
    vectorizer = TfidfVectorizer(
        max_features=500,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1
    )

    try:
        X = vectorizer.fit_transform(pain_points)
    except Exception as e:
        print(f"[cluster] Vectorization failed: {e}")
        return []

    # ── KMeans Clustering ─────────────────────────────────────────────────────
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10,
        max_iter=300
    )

    try:
        labels = kmeans.fit_predict(X)
    except Exception as e:
        print(f"[cluster] KMeans failed: {e}")
        return []

    # ── Build cluster objects ─────────────────────────────────────────────────
    cluster_map = {}

    for idx, label in enumerate(labels):
        if label not in cluster_map:
            cluster_map[label] = {
                "pain_points": [],
                "quotes": [],
                "indices": []
            }
        cluster_map[label]["pain_points"].append(pain_points[idx])
        cluster_map[label]["quotes"].append(complaints[idx]["text"][:400])
        cluster_map[label]["indices"].append(idx)

    # ── Generate label for each cluster ──────────────────────────────────────
    feature_names = vectorizer.get_feature_names_out()
    cluster_centers = kmeans.cluster_centers_

    clusters = []

    for cluster_id, data in cluster_map.items():
        count = len(data["pain_points"])

        # Get top TF-IDF terms for this cluster center as label
        center = cluster_centers[cluster_id]
        top_indices = np.argsort(center)[::-1][:4]
        top_terms = [feature_names[i] for i in top_indices if center[i] > 0]
        label = " · ".join(top_terms[:3]).title() if top_terms else f"Problem Group {cluster_id + 1}"

        # Score = count (frequency is most important for MVP)
        score = count

        # Pick best example quotes (shortest clean ones first)
        sorted_quotes = sorted(data["quotes"], key=lambda q: len(q))
        best_quotes = sorted_quotes[:3]

        clusters.append({
            "label": label,
            "count": count,
            "score": score,
            "quotes": best_quotes
        })

    # ── Sort by count descending ──────────────────────────────────────────────
    clusters.sort(key=lambda x: x["score"], reverse=True)

    return clusters
