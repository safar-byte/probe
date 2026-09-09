#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Jina AI embeddings client — used to embed runbooks at seed time and the
Correlator's diagnosis text at query time, per the PDF's stated stack."""

import os

import httpx

_JINA_EMBEDDINGS_URL = "https://api.jina.ai/v1/embeddings"


class JinaClient:
    def __init__(self):
        self._api_key = os.environ["JINA_API_KEY"]
        self._model = os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v3")

    def embed(self, texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            _JINA_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={"model": self._model, "input": texts},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()["data"]
        # Jina returns results possibly out of input order; sort by index to be safe.
        data.sort(key=lambda d: d["index"])
        return [d["embedding"] for d in data]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
