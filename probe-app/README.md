# PROBE

Hackathon entry for **Forge the Future 2026 (Elastic + AWS Bedrock track)** —
see `../idea/probe.pdf` for the pitch.

This is a **standalone project**, deliberately separate from
`../astronomy-shop-elastic`. That repo is just the running app PROBE
observes and injects faults into (via its own docker compose, with the
ability to enable/disable each service) — it has its own lifecycle and
shouldn't be coupled to this hackathon add-on. PROBE reaches it over its
published host ports (`localhost:8080` for the app/flagd-ui,
`localhost:4318` for OTel ingestion), the same way any external tool would.

## Layout

```
docker-compose.yml     # standalone compose project ("probe")
.env                    # all config/secrets for this project
detector/                {Dockerfile, requirements.txt, run.py, src/detector/...}
correlator/               {..., src/correlator/graph/dependency_graph.json}
remediator/                {..., src/remediator/..., runbooks/*.md}
dashboard/              server.py, static/index.html — the live demo UI
harness/                run_eval.py, faults.yaml, results/
shared/                 otel_bootstrap.py (used by all three agent services)
```

## What's built

- **`detector/`** — FastAPI service. `POST /scan` runs ES|QL queries
  (error rate, p95 latency, log error bursts) over Elastic's OTel-native
  data streams (`traces-*.otel-default`, `logs-*.otel-default`) and
  returns a client-side z-score anomaly list per service.
- **`correlator/`** — FastAPI service. `POST /correlate` sends the
  anomaly list + a static service dependency graph
  (`correlator/src/correlator/graph/dependency_graph.json`) to Claude on
  Amazon Bedrock (Converse API, tool-use forced JSON output) and returns a
  single root-cause diagnosis.
- **`remediator/`** — FastAPI service. `POST /remediate` embeds the
  diagnosis via Jina AI, kNN-searches a `probe-runbooks` Elasticsearch
  index (seeded from `remediator/runbooks/*.md`, 13 hand-authored
  runbooks, one per flagd fault) for the closest fix, then always creates
  a Kibana Case and — if `JIRA_*` env vars are set — also creates a Jira
  issue (best-effort, never blocks the Kibana path).
- **`harness/run_eval.py`** — the self-grading harness and the literal
  demo script. Injects each curated fault in `harness/faults.yaml` via
  astronomy-shop-elastic's `flagd-ui` API, times how long PROBE takes to
  correctly name the root cause, resets the flag, and prints/saves the
  "X/10 at mean Ys" scoreboard plus the dumb threshold-baseline
  comparison. Runs directly on the host (not containerized) — it's also
  the thing you run live on stage.
- **`dashboard/`** — a real, running frontend at `localhost:8023` for the
  live demo: pick a fault, hit "Inject & diagnose", and watch the
  Detector → Correlator → Remediator pipeline execute for real —
  anomalies, the Bedrock diagnosis, confidence, reasoning, the matched
  runbook, and the resulting Kibana Case/Jira issue all render as each
  stage actually completes, with a running stopwatch and a live
  correct/wrong verdict against the fault's known answer. `server.py` is
  a thin FastAPI service that proxies every call server-to-server (to
  Detector/Correlator/Remediator by container name, to flagd-ui via
  `host.docker.internal`) so the browser only ever talks to one
  same-origin service — no CORS wiring needed on the other three.

## Stage 0 — what you still need to provide

Fill these into `.env` (placeholders already there with the right names):

1. **AWS Bedrock** — request model access for a Claude model (region
   `ap-south-1` per the pitch, or agree a fallback like `us-east-1`).
   Set `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
   `BEDROCK_MODEL_ID` (a bare model ID or an inference-profile ARN,
   depending on the model).
2. **A new, read-scoped Elastic API key** — `read`+`monitor` on
   `traces-*`, `metrics-*`, `logs-*`, plus `write` on `probe-runbooks` and
   `probe-eval-results`. Set `ELASTIC_API_KEY_READ`. **Do not reuse**
   astronomy-shop-elastic's `ELASTIC_OTLP_API_KEY` — that one is
   ingest-only (confirmed via a 403). Verify `ELASTIC_ES_URL` in the
   Elastic Cloud console, and set `KIBANA_URL`.
3. **Jina AI** — an API key for the embeddings API. Set `JINA_API_KEY`.
4. **Jira** (optional — second ticket path) — `JIRA_BASE_URL`,
   `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`. Leave blank to skip.
5. **Elastic Agent Builder / Workflows** — check in Kibana whether these
   are enabled on your Serverless project. Nothing here depends on it —
   it was a "verify first" item, not a blocker.

## Bringing it up

1. Start `../astronomy-shop-elastic` first (it must be up and reachable on
   `localhost:8080`/`localhost:4318` before these services are useful).
2. Once at least `ELASTIC_API_KEY_READ`/`ELASTIC_ES_URL` are set:

```sh
docker compose up --build --detach
```

3. Seed the runbook index once `JINA_API_KEY`/`ELASTIC_API_KEY_READ` are
   set:

```sh
pip install -r remediator/requirements.txt
python -m src.remediator.runbook_index   # run from inside remediator/, with .env's vars exported
```

4. Open the live demo UI at **http://localhost:8023** — pick a fault from
   the dropdown and click "Inject & diagnose" to watch the real pipeline
   run.

5. Or run the harness from the host for the full graded batch (also works
   standalone, without the dashboard open):

```sh
pip install -r harness/requirements.txt
python harness/run_eval.py
```

## Operating it — stopping and starting

Both projects are independent `docker compose` stacks — commands below run
from each project's own root (no need to `cd` into a subfolder; each
`docker-compose.yml`/`compose.yaml` lives at that root).

**Order matters on startup**: bring `astronomy-shop-elastic` up before
`probe-app` — the Detector and Dashboard reach it over `localhost:8080` /
`localhost:4318`.

### astronomy-shop-elastic (the demo app)

```sh
cd path/to/astronomy-shop-elastic

# start
docker compose --env-file .env --env-file .env.override \
  -f compose.yaml -f compose.full.yaml -f compose.observability.yaml \
  -f compose.extras.yaml -f docker-compose.elastic.yml \
  up --detach

# stop (keeps containers, just stops them — fast to start again)
docker compose --env-file .env --env-file .env.override \
  -f compose.yaml -f compose.full.yaml -f compose.observability.yaml \
  -f compose.extras.yaml -f docker-compose.elastic.yml \
  stop

# start again (no rebuild needed)
docker compose --env-file .env --env-file .env.override \
  -f compose.yaml -f compose.full.yaml -f compose.observability.yaml \
  -f compose.extras.yaml -f docker-compose.elastic.yml \
  start

# tear down completely (removes containers/network, not volumes)
docker compose --env-file .env --env-file .env.override \
  -f compose.yaml -f compose.full.yaml -f compose.observability.yaml \
  -f compose.extras.yaml -f docker-compose.elastic.yml \
  down
```

### probe-app (Detector / Correlator / Remediator / Dashboard)

```sh
cd path/to/probe-app

docker compose up --detach     # start
docker compose stop            # stop
docker compose start           # start again
docker compose down            # tear down completely
```

### Handy extras (either project)

- **Status**: `docker compose ps`
- **Live logs, one service**: `docker compose logs -f probe-correlator` (swap the name — `otel-collector`, `probe-detector`, etc.)
- **Pick up an `.env`/`.env.override` edit** without a full restart: `docker compose up --detach --force-recreate <service-name>`

## Verification checklist

- `curl -X POST http://localhost:8020/scan` returns anomalies after
  manually flipping one flag (e.g. `paymentFailure` to `100%`) in
  astronomy-shop-elastic's flagd UI at `http://localhost:8080/feature`.
- `curl -X POST http://localhost:8021/correlate -d '{"anomalies": [...]}'`
  returns valid structured JSON naming the right service for at least
  `paymentFailure` and `cartFailure`.
- A Kibana Case actually appears in Kibana after a `/remediate` call.
- `python harness/run_eval.py` runs end-to-end on all 10 curated faults
  and leaves all flags reset to `off` afterward (`GET
  http://localhost:8080/feature/api/read`).

## Not yet done

Kibana dashboard over `probe-eval-results`, and rehearsal of the live
flip-fault → diagnose → grade loop. Do this last, after a few real harness
runs succeed.
