"""Restore the public regulation corpus without downloading models or calling APIs."""
import io
import json
from pathlib import Path
import zipfile

import numpy as np


def restore_seed(collection, bundle: Path, model_name: str) -> int:
    """Import missing seed IDs once per version; retry safely after interruption."""
    if not bundle.is_file():
        return 0
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        metadata = dict(collection.metadata or {})
        if metadata.get("regulation_seed_version") == manifest["version"]:
            return 0
        if manifest["embedding_model"] != model_name:
            raise ValueError("预置知识库使用 BAAI/bge-m3；请将 EMBEDDING_MODEL_NAME 设置为该模型。")
        records = [json.loads(line) for line in archive.read("chunks.jsonl").decode("utf-8").splitlines()]
        vectors = np.load(io.BytesIO(archive.read("vectors.npy")), allow_pickle=False)
    if len(records) != manifest["chunks"] or vectors.shape != (len(records), manifest["dimension"]):
        raise ValueError("预置知识库文件不完整，请重新下载 knowledge/seed.zip。")
    if not np.isfinite(vectors).all() or len({r["id"] for r in records}) != len(records):
        raise ValueError("预置知识库向量或标识无效。")
    existing = set(collection.get(include=[])['ids'])
    pending = [i for i, record in enumerate(records) if record["id"] not in existing]
    for start in range(0, len(pending), 256):
        indices = pending[start:start + 256]
        collection.upsert(
            ids=[records[i]["id"] for i in indices],
            documents=[records[i]["document"] for i in indices],
            metadatas=[records[i]["metadata"] for i in indices],
            embeddings=vectors[indices].tolist(),
        )
    metadata["regulation_seed_version"] = manifest["version"]
    collection.modify(metadata=metadata)
    return len(pending)
