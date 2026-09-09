#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""PROBE dashboard — a real, running frontend for the live demo.

Serves the UI and proxies every call server-to-server (dashboard -> Detector
/ Correlator / Remediator / flagd-ui) so the browser only ever talks to this
one same-origin service. That sidesteps CORS entirely instead of adding it
to four different services, and keeps every cross-service base URL in one
place (env vars below).
"""

import logging
import os
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)

DETECTOR_URL = os.environ["DASHBOARD_DETECTOR_URL"]
CORRELATOR_URL = os.environ["DASHBOARD_CORRELATOR_URL"]
REMEDIATOR_URL = os.environ["DASHBOARD_REMEDIATOR_URL"]
FLAGD_UI_URL = os.environ["DASHBOARD_FLAGD_URL"]

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI()


class FlagRequest(BaseModel):
    flag: str
    variant: str


class CorrelateRequest(BaseModel):
    anomalies: list[dict]


class RemediateRequest(BaseModel):
    root_cause_service: str
    root_cause_signal: str
    confidence: float
    reasoning: str
    symptom_services: list[str] = []


async def _get(client: httpx.AsyncClient, url: str, **kwargs) -> dict:
    response = await client.get(url, timeout=15.0, **kwargs)
    response.raise_for_status()
    return response.json()


async def _post(client: httpx.AsyncClient, url: str, **kwargs) -> dict:
    response = await client.post(url, timeout=60.0, **kwargs)
    response.raise_for_status()
    return response.json()


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    targets = {"detector": DETECTOR_URL, "correlator": CORRELATOR_URL, "remediator": REMEDIATOR_URL}
    result = {}
    async with httpx.AsyncClient() as client:
        for name, base_url in targets.items():
            try:
                await _get(client, f"{base_url}/healthz")
                result[name] = "up"
            except Exception as e:
                logging.warning("%s unreachable: %s", name, e)
                result[name] = "down"
    return result


@app.get("/api/flags")
async def get_flags():
    async with httpx.AsyncClient() as client:
        try:
            return await _get(client, f"{FLAGD_UI_URL}/api/read")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"flagd-ui unreachable: {e}") from e


@app.post("/api/flags/set")
async def set_flag(request: FlagRequest):
    """Read-modify-write a single flag's defaultVariant, leaving every other
    flag untouched — flagd-ui's write endpoint replaces the whole file."""
    async with httpx.AsyncClient() as client:
        try:
            config = await _get(client, f"{FLAGD_UI_URL}/api/read")
            if request.flag not in config["flags"]:
                raise HTTPException(status_code=404, detail=f"Unknown flag: {request.flag}")
            config["flags"][request.flag]["defaultVariant"] = request.variant
            await _post(client, f"{FLAGD_UI_URL}/api/write", json={"data": config})
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"flagd-ui unreachable: {e}") from e
    return {"flag": request.flag, "defaultVariant": request.variant}


@app.post("/api/pipeline/scan")
async def scan():
    async with httpx.AsyncClient() as client:
        try:
            return await _post(client, f"{DETECTOR_URL}/scan")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Detector unreachable: {e}") from e


@app.post("/api/pipeline/correlate")
async def correlate(request: CorrelateRequest):
    async with httpx.AsyncClient() as client:
        try:
            return await _post(client, f"{CORRELATOR_URL}/correlate", json=request.model_dump())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Correlator error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Correlator unreachable: {e}") from e


@app.post("/api/pipeline/remediate")
async def remediate(request: RemediateRequest):
    async with httpx.AsyncClient() as client:
        try:
            return await _post(client, f"{REMEDIATOR_URL}/remediate", json=request.model_dump())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Remediator error: {e.response.text}") from e
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Remediator unreachable: {e}") from e


if __name__ == "__main__":
    port = int(os.getenv("PROBE_DASHBOARD_PORT", "8023"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
