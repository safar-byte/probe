#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.correlator.llm_client import get_correlator

_GRAPH_PATH = Path(__file__).parent / "graph" / "dependency_graph.json"


class CorrelateRequest(BaseModel):
    anomalies: list[dict]


class Correlator:
    def __init__(self):
        self.app = FastAPI()
        self.app.get("/healthz")(self.healthz)
        self.app.post("/correlate")(self.correlate)
        self._llm = None
        with open(_GRAPH_PATH) as f:
            self._dependency_graph = json.load(f)

    async def healthz(self):
        return {"status": "ok"}

    def _client(self):
        if self._llm is None:
            self._llm = get_correlator()
        return self._llm

    async def correlate(self, request: CorrelateRequest):
        if not request.anomalies:
            return {
                "root_cause_service": None,
                "root_cause_signal": None,
                "confidence": 0.0,
                "reasoning": "No anomalies supplied.",
                "symptom_services": [],
            }
        try:
            diagnosis = self._client().diagnose(request.anomalies, self._dependency_graph)
        except Exception as e:
            logging.exception("LLM correlation failed")
            raise HTTPException(status_code=502, detail=str(e)) from e
        return diagnosis

    async def launch(self):
        port = int(os.getenv("PROBE_CORRELATOR_PORT", "8021"))
        config = uvicorn.Config(app=self.app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
