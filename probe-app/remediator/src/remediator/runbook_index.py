#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Loads runbooks/*.md, embeds them via Jina, and indexes them into a new
`probe-runbooks` Elasticsearch index with a dense_vector field. Elastic
applies its own on-disk quantization (DiskBBQ) to that field automatically
at this index size/type — there is no separate DiskBBQ code to write.

Run as a one-off seed step (`python -m src.remediator.runbook_index`)
before the Remediator serves traffic — the index only needs rebuilding
when a runbook's content changes.
"""

import logging
import os
from pathlib import Path

import yaml
from elasticsearch import Elasticsearch

from src.remediator.jina_client import JinaClient

RUNBOOKS_DIR = Path(__file__).resolve().parents[2] / "runbooks"
INDEX_NAME = "probe-runbooks"


def _parse_runbook(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    return {
        "fault_signature": meta["fault_signature"],
        "service": meta["service"],
        "title": meta["title"],
        "body": body.strip(),
    }


def load_runbooks() -> list[dict]:
    return [_parse_runbook(p) for p in sorted(RUNBOOKS_DIR.glob("*.md"))]


def _es_client() -> Elasticsearch:
    return Elasticsearch(os.environ["ELASTIC_ES_URL"], api_key=os.environ["ELASTIC_API_KEY_READ"])


def seed_index(embedding_dims: int = 1024):
    es = _es_client()
    jina = JinaClient()
    runbooks = load_runbooks()

    if not es.indices.exists(index=INDEX_NAME):
        es.indices.create(
            index=INDEX_NAME,
            mappings={
                "properties": {
                    "fault_signature": {"type": "keyword"},
                    "service": {"type": "keyword"},
                    "title": {"type": "text"},
                    "body": {"type": "text"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": embedding_dims,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            },
        )

    embeddings = jina.embed([f"{r['title']}\n{r['body']}" for r in runbooks])
    for runbook, embedding in zip(runbooks, embeddings):
        es.index(
            index=INDEX_NAME,
            id=runbook["fault_signature"],
            document={**runbook, "embedding": embedding},
        )
    logging.info("Seeded %d runbooks into %s", len(runbooks), INDEX_NAME)


def search_runbooks(es: Elasticsearch, jina: JinaClient, query_text: str, k: int = 3) -> list[dict]:
    query_vector = jina.embed_one(query_text)
    response = es.search(
        index=INDEX_NAME,
        knn={
            "field": "embedding",
            "query_vector": query_vector,
            "k": k,
            "num_candidates": max(k * 5, 20),
        },
    )
    return [hit["_source"] for hit in response["hits"]["hits"]]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from dotenv import load_dotenv

    load_dotenv()
    seed_index()
