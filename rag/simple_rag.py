# Simple RAG using TF-IDF; persists to data/rag_index.pkl
import pickle
from pathlib import Path
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
INDEX_PATH = DATA_DIR / "rag_index.pkl"

def _load_index():
    if INDEX_PATH.exists():
        with INDEX_PATH.open("rb") as f:
            return pickle.load(f)
    return {"docs": [], "meta": [], "vectorizer": None, "matrix": None, "namespaces": []}

def _save_index(idx):
    with INDEX_PATH.open("wb") as f:
        pickle.dump(idx, f)

def ingest_text(name: str, text: str, namespace: str = "default"):
    idx = _load_index()
    idx["docs"].append(text)
    idx["meta"].append({"name": name, "namespace": namespace})
    idx["namespaces"].append(namespace)
    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english")
    mat = vectorizer.fit_transform(idx["docs"])
    idx["vectorizer"] = vectorizer
    idx["matrix"] = mat
    _save_index(idx)
    return {"count": len(idx["docs"]), "namespaces": list(set(idx["namespaces"]))}

def search(query: str, top_k: int = 5, namespace: str | None = None) -> List[Dict]:
    idx = _load_index()
    if not idx["vectorizer"] or idx["matrix"] is None or len(idx["docs"]) == 0:
        return []
    qv = idx["vectorizer"].transform([query])
    sims = cosine_similarity(qv, idx["matrix"]).ravel()
    order = sims.argsort()[::-1]
    results = []
    for i in order:
        m = idx["meta"][i]
        if namespace and m.get("namespace") != namespace:
            continue
        results.append({
            "score": float(sims[i]),
            "name": m.get("name"),
            "namespace": m.get("namespace"),
            "snippet": idx["docs"][i][:400]
        })
        if len(results) >= top_k:
            break
    return results
