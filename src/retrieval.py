"""Chunk the data dictionary, embed it, index it in Chroma, and retrieve relevant tables."""
import json
import re
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

DICT_PATH = Path("data/data_dictionary.json")
CHROMA_DIR = "chroma_db"
COLLECTION = "chinook_dictionary"
MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_CACHE = "models_cache"
GROUP_SIZE = 5  # columns per column-group chunk

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:  # load once, reuse (loading is the slow part)
        _model = TextEmbedding(MODEL_NAME, cache_dir=MODEL_CACHE)
    return _model


def embed(texts):
    return [v.tolist() for v in _get_model().embed(texts)]


def _client():
    return chromadb.PersistentClient(
        path=CHROMA_DIR, settings=Settings(anonymized_telemetry=False))


def build_chunks(dictionary):
    """Return a list of {id, table, kind, text} chunks."""
    chunks = []
    for tb in dictionary:
        name, desc, cols = tb["table"], tb["description"], tb["columns"]
        fks = [f'{c["name"]} -> {c["foreign_key"]}' for c in cols if c["foreign_key"]]
        overview = f'Table {name}: {desc} Columns: {", ".join(c["name"] for c in cols)}.'
        if fks:
            overview += " Foreign keys: " + "; ".join(fks) + "."
        chunks.append({"id": f"{name}::overview", "table": name,
                       "kind": "overview", "text": overview})
        for i in range(0, len(cols), GROUP_SIZE):
            lines = [
                f'{c["name"]} ({c["type"]}): {c["description"]} '
                f'Examples: {", ".join(c["examples"])}'
                for c in cols[i:i + GROUP_SIZE]
            ]
            chunks.append({"id": f"{name}::cols{i // GROUP_SIZE}", "table": name,
                           "kind": "columns",
                           "text": f"Table {name}: {desc} Column details: " + " | ".join(lines)})
    return chunks


def build_index():
    dictionary = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    chunks = build_chunks(dictionary)
    client = _client()
    try:
        client.delete_collection(COLLECTION)  # rebuild from scratch each time
    except Exception:
        pass
    col = client.create_collection(COLLECTION)
    texts = [c["text"] for c in chunks]
    col.add(
        ids=[c["id"] for c in chunks],
        documents=texts,
        embeddings=embed(texts),
        metadatas=[{"table": c["table"], "kind": c["kind"]} for c in chunks],
    )
    return len(chunks)


def _get_collection():
    global _collection
    if _collection is None:
        _collection = _client().get_collection(COLLECTION)
    return _collection


def _tokens(text):
    """Lowercase word pieces; InvoiceLine -> invoice line; crude plural stripping."""
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return [t[:-1] if len(t) > 3 and t.endswith("s") else t
            for t in re.findall(r"[a-z0-9]+", text.lower())]


@lru_cache(maxsize=1)
def _bm25():
    chunks = build_chunks(json.loads(DICT_PATH.read_text(encoding="utf-8")))
    return BM25Okapi([_tokens(c["text"]) for c in chunks]), chunks


@lru_cache(maxsize=1)
def _fk_neighbors():
    """table -> set of tables linked to it by a foreign key (either direction)."""
    nb = {}
    for tb in json.loads(DICT_PATH.read_text(encoding="utf-8")):
        for c in tb["columns"]:
            if c["foreign_key"]:
                other = c["foreign_key"].split(".")[0]
                nb.setdefault(tb["table"], set()).add(other)
                nb.setdefault(other, set()).add(tb["table"])
    return nb


def _dense_scores(question, n_chunks):
    """table -> {score, chunk} from the best-matching chunk (cosine-like, higher = better)."""
    col = _get_collection()
    res = col.query(query_embeddings=embed([question]),
                    n_results=min(n_chunks, col.count()))
    best = {}
    for meta, dist, doc in zip(res["metadatas"][0], res["distances"][0], res["documents"][0]):
        t, s = meta["table"], 1 - dist / 2  # squared-L2 on unit vectors -> cosine
        if t not in best or s > best[t]["score"]:
            best[t] = {"score": s, "chunk": doc}
    return best


def _bm25_scores(question):
    """table -> {score, chunk} from BM25 keyword matching over the same chunks."""
    bm25, chunks = _bm25()
    best = {}
    for c, s in zip(chunks, bm25.get_scores(_tokens(question))):
        if s > 0 and (c["table"] not in best or s > best[c["table"]]["score"]):
            best[c["table"]] = {"score": float(s), "chunk": c["text"]}
    return best


def _rrf(*score_dicts, c=60):
    """Reciprocal Rank Fusion: combine rankings using only ranks, so scales don't matter."""
    fused = {}
    for sd in score_dicts:
        order = sorted(sd, key=lambda t: -sd[t]["score"])
        for rank, t in enumerate(order, 1):
            entry = fused.setdefault(t, {"score": 0.0, "chunk": sd[t]["chunk"]})
            entry["score"] += 1 / (c + rank)
    return fused


def _fk_expand(scores, boost, n_parents=2):
    """Rerank: tables linked by a foreign key to the top tables get a score boost."""
    out = {t: dict(v) for t, v in scores.items()}
    top = sorted(scores, key=lambda t: -scores[t]["score"])[:n_parents]
    for parent in top:
        for nb in _fk_neighbors().get(parent, ()):
            s = scores[parent]["score"] * boost
            if nb not in out:
                out[nb] = {"score": s, "chunk": f"(added via foreign key from {parent})"}
            elif s > out[nb]["score"]:
                out[nb]["score"] = s
    return out


def retrieve(question, k=3, n_chunks=10, mode="dense", fk_expand=False, fk_boost=0.8):
    """Top-k tables: [{table, score, chunk}, ...]. mode: dense | bm25 | hybrid."""
    if mode == "dense":
        scores = _dense_scores(question, n_chunks)
    elif mode == "bm25":
        scores = _bm25_scores(question)
    elif mode == "hybrid":
        scores = _rrf(_dense_scores(question, n_chunks), _bm25_scores(question))
    else:
        raise ValueError(f"unknown mode: {mode}")
    if fk_expand:
        scores = _fk_expand(scores, fk_boost)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1]["score"])[:k]
    return [{"table": t, "score": v["score"], "chunk": v["chunk"]} for t, v in ranked]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "build":
        print(f"Indexed {build_index()} chunks")
    else:
        for r in retrieve(" ".join(sys.argv[1:])):
            print(f'{r["table"]:15} score={r["score"]:.3f}')