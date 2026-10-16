"""Exercise the shipped corpus against a new on-disk vector database."""
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest

from core.vectorstore.chroma_store import ChromaStore
from core.vectorstore.seed import restore_seed


class OfflineEmbedder:
    model_name = "BAAI/bge-m3"

    def embed_texts(self, texts):
        raise AssertionError("Seed restoration must not call an embedding service")


def test_full_corpus_restores_and_survives_repeat_start(tmp_path):
    bundle = Path(__file__).resolve().parents[1] / "knowledge/seed.zip"
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        records = [json.loads(line) for line in archive.read("chunks.jsonl").decode().splitlines()]
        vectors = np.load(io.BytesIO(archive.read("vectors.npy")), allow_pickle=False)
    store = ChromaStore(tmp_path / "chroma", OfflineEmbedder(), seed_path=bundle)
    assert store.collection.count() == manifest["chunks"] == 4235
    assert sorted(store.list_sources()) == manifest["sources"]
    assert len(store.list_sources()) == 17
    sample = next(i for i, record in enumerate(records) if "CCAR-92" in record["metadata"]["source_file"])
    result = store.collection.query(
        query_embeddings=[vectors[sample].tolist()], n_results=1,
        where={"source_file": records[sample]["metadata"]["source_file"]},
    )
    # Some documents contain identical headings; IDs need not be unique at distance zero.
    assert result["distances"][0][0] < 1e-6
    assert restore_seed(store.collection, bundle, OfflineEmbedder.model_name) == 0
    # A user's intentional removal is not undone on every rerun.
    store.collection.delete(ids=[records[sample]["id"]])
    assert restore_seed(store.collection, bundle, OfflineEmbedder.model_name) == 0
    assert store.collection.count() == 4234


def test_seed_rejects_incompatible_model(tmp_path):
    bundle = Path(__file__).resolve().parents[1] / "knowledge/seed.zip"
    store = ChromaStore(tmp_path / "chroma", OfflineEmbedder())
    with pytest.raises(ValueError, match="BAAI/bge-m3"):
        restore_seed(store.collection, bundle, "different-model")
    assert store.collection.count() == 0
