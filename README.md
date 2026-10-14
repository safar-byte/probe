<div align="center">

# 🔍 PROBE

**Autonomous incident triage for microservices — detect, diagnose and open the ticket before a human is paged.**

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-005571?style=flat-square&logo=elasticsearch&logoColor=white)
![AWS Bedrock](https://img.shields.io/badge/AWS_Bedrock-232F3E?style=flat-square&logo=amazonwebservices&logoColor=white)
![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-425CC7?style=flat-square&logo=opentelemetry&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)

*Hackathon entry — Forge the Future 2026 (Elastic + AWS Bedrock track)*

</div>

---

## Overview

PROBE watches a running microservice system through its OpenTelemetry data in Elastic, notices when something goes wrong, works out **which service is the root cause**, finds the matching runbook and opens a Kibana Case (and optionally a Jira issue) — end to end, with no human in the loop.

It is demoed against the OpenTelemetry **Astronomy Shop** sample app: a fault is injected through the app's feature-flag UI, and PROBE is timed on how quickly it names the right culprit.

## How it works

```
 OTel traces & logs ──► Elastic
                          │
                          ▼
 ┌──────────┐  anomalies  ┌────────────┐  diagnosis  ┌────────────┐
 │ Detector │ ──────────► │ Correlator │ ──────────► │ Remediator │ ──► Kibana Case / Jira
 └──────────┘             └────────────┘             └────────────┘
  ES|QL + z-scores         Claude on Bedrock           Jina embeddings +
  per service              + service dependency graph  kNN runbook search
```

| Service | Role |
|---|---|
| **Detector** | `POST /scan` runs ES\|QL queries (error rate, p95 latency, log error bursts) over OTel data streams and returns a z-score anomaly list per service. |
| **Correlator** | `POST /correlate` sends the anomalies plus a static dependency graph to Claude on Amazon Bedrock (tool-use forced JSON) and returns a single root-cause diagnosis with confidence and reasoning. |
| **Remediator** | `POST /remediate` embeds the diagnosis, kNN-searches 13 hand-written runbooks in Elasticsearch, and opens a Kibana Case (plus a Jira issue if configured). |
| **Dashboard** | Live demo UI at `localhost:8023` — pick a fault, hit *Inject & diagnose*, and watch each stage complete with a running stopwatch and a correct/wrong verdict. |
| **Harness** | `harness/run_eval.py` injects every curated fault, times the diagnosis, resets the flag and prints an "X/10 at mean Ys" scoreboard against a simple threshold baseline. |

## Repository layout

```
probe-app/              # the PROBE services (standalone docker compose project)
  detector/  correlator/  remediator/  dashboard/  harness/  shared/
astronomy-shop/         # upstream OpenTelemetry demo (the system under observation)
astronomy-shop-elastic/ # the demo wired to Elastic
idea/probe.pdf          # the pitch deck
```

## Getting started

**Prerequisites:** Docker Desktop, an Elastic Cloud deployment receiving the Astronomy Shop's OTel data, AWS Bedrock model access (or an Anthropic / OpenAI / Gemini key for local testing) and a Jina AI key.

```bash
cd probe-app
# fill in probe-app/.env with your own keys (see probe-app/README.md)
docker compose up -d
# dashboard → http://localhost:8023

python harness/run_eval.py  # run the self-grading benchmark
```

Detailed configuration notes are in [`probe-app/README.md`](probe-app/README.md).

## Tech stack

Python · FastAPI · Elasticsearch ES|QL · Kibana Cases · Amazon Bedrock (Claude) · Jina AI embeddings · OpenTelemetry · Docker Compose

## Author

**Muhammed Safar** — [@safar-byte](https://github.com/safar-byte)
