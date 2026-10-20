"""Chunk the data dictionary, embed it, index it in Chroma, and retrieve relevant tables."""
import json
from pathlib import Path

import chromadb
from chromadb.config import Settings
from fastembed import TextEmbedding

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


def retrieve(question, k=3, n_chunks=10):
    """Return the top-k tables for a question: [{table, distance, chunk}, ...]."""
    col = _get_collection()
    res = col.query(query_embeddings=embed([question]),
                    n_results=min(n_chunks, col.count()))
    best = {}  # table -> its best (lowest-distance) chunk
    for meta, dist, doc in zip(res["metadatas"][0], res["distances"][0], res["documents"][0]):
        t = meta["table"]
        if t not in best or dist < best[t]["distance"]:
            best[t] = {"table": t, "distance": dist, "chunk": doc}
    return sorted(best.values(), key=lambda r: r["distance"])[:k]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "build":
        print(f"Indexed {build_index()} chunks")
    else:
        for r in retrieve(" ".join(sys.argv[1:])):
            print(f'{r["table"]:15} distance={r["distance"]:.3f}')