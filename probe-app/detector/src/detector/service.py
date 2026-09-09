#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import uvicorn
from fastapi import FastAPI

from src.detector.anomaly import score_anomalies
from src.detector.es_client import ESClient
from src.detector.queries import (
    error_rate_by_service,
    latency_p95_by_service,
    log_error_burst_by_service,
)


class Detector:
    def __init__(self):
        self.app = FastAPI()
        self.app.get("/healthz")(self.healthz)
        self.app.post("/scan")(self.scan)
        self._es = None

    async def healthz(self):
        return {"status": "ok"}

    def _client(self) -> ESClient:
        if self._es is None:
            self._es = ESClient()
        return self._es

    async def scan(self):
        """Run the fixed battery of anomaly queries and return a raw,
        deliberately over-inclusive candidate list. Narrowing to a single
        root cause is the Correlator's job, not this service's."""
        es = self._client()
        anomalies = []

        try:
            rows = es.esql_rows(error_rate_by_service())
            anomalies += score_anomalies(rows, "error_rate", "trace_error_rate", "error_rate")
        except Exception as e:
            logging.warning("error_rate query failed: %s", e)

        try:
            rows = es.esql_rows(latency_p95_by_service())
            anomalies += score_anomalies(rows, "p95_ns", "trace_latency_p95", "duration_p95_ns")
        except Exception as e:
            logging.warning("latency query failed: %s", e)

        try:
            rows = es.esql_rows(log_error_burst_by_service())
            anomalies += score_anomalies(rows, "error_count", "log_error_burst", "error_count")
        except Exception as e:
            logging.warning("log error burst query failed: %s", e)

        return {"anomalies": anomalies}

    async def launch(self):
        port = int(os.getenv("PROBE_DETECTOR_PORT", "8020"))
        config = uvicorn.Config(app=self.app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
