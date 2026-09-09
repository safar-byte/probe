#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import logging
import os

import uvicorn
from elasticsearch import Elasticsearch
from fastapi import FastAPI
from pydantic import BaseModel

from src.remediator.jina_client import JinaClient
from src.remediator.jira_client import JiraClient, jira_configured
from src.remediator.kibana_client import KibanaCaseClient
from src.remediator.runbook_index import search_runbooks


class Diagnosis(BaseModel):
    root_cause_service: str
    root_cause_signal: str
    confidence: float
    reasoning: str
    symptom_services: list[str] = []


class Remediator:
    def __init__(self):
        self.app = FastAPI()
        self.app.get("/healthz")(self.healthz)
        self.app.post("/remediate")(self.remediate)
        self._es = None
        self._jina = None
        self._kibana = None

    async def healthz(self):
        return {"status": "ok"}

    def _es_client(self) -> Elasticsearch:
        if self._es is None:
            self._es = Elasticsearch(os.environ["ELASTIC_ES_URL"], api_key=os.environ["ELASTIC_API_KEY_READ"])
        return self._es

    def _jina_client(self) -> JinaClient:
        if self._jina is None:
            self._jina = JinaClient()
        return self._jina

    def _kibana_client(self) -> KibanaCaseClient:
        if self._kibana is None:
            self._kibana = KibanaCaseClient()
        return self._kibana

    async def remediate(self, diagnosis: Diagnosis):
        diagnosis_dict = diagnosis.model_dump()
        query_text = f"{diagnosis.root_cause_service} {diagnosis.root_cause_signal} {diagnosis.reasoning}"

        runbook = None
        try:
            matches = search_runbooks(self._es_client(), self._jina_client(), query_text, k=1)
            runbook = matches[0] if matches else None
        except Exception as e:
            logging.warning("Runbook retrieval failed, continuing without one: %s", e)

        result = {"runbook": runbook, "kibana_case": None, "jira_issue": None, "jira_error": None}

        # Primary path — must succeed reliably for the demo; let a failure raise.
        result["kibana_case"] = self._kibana_client().create_case(diagnosis_dict, runbook)

        # Secondary path — isolated; never let a Jira failure break the response.
        if jira_configured():
            try:
                result["jira_issue"] = JiraClient().create_issue(diagnosis_dict, runbook)
            except Exception as e:
                logging.warning("Jira ticket creation failed, continuing: %s", e)
                result["jira_error"] = str(e)

        return result

    async def launch(self):
        port = int(os.getenv("PROBE_REMEDIATOR_PORT", "8022"))
        config = uvicorn.Config(app=self.app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
