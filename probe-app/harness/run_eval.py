#!/usr/bin/env python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""PROBE self-grading harness — the literal demo script.

For each curated fault (faults.yaml): flips the flagd flag on via
flagd-ui's read-modify-write API, waits for the Detector/Correlator to
diagnose it, checks the diagnosis against the known ground truth, and
resets the flag before moving on. Also runs a deliberately dumb
fixed-threshold check in parallel to produce the baseline comparison.

Run from the host once the stack (including compose.probe.yaml) is up:

    pip install -r src/probe-harness/requirements.txt
    python src/probe-harness/run_eval.py
"""

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

import httpx
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("probe-harness")

HERE = Path(__file__).parent
FAULTS_PATH = HERE / "faults.yaml"
RESULTS_DIR = HERE / "results"

# All routed through frontend-proxy on 8080, matching src/flagd-ui/README.md's
# own example (not FLAGD_UI_PORT directly — that's not published to the host).
FLAGD_UI_URL = os.getenv("PROBE_FLAGD_UI_URL", "http://localhost:8080/feature")
DETECTOR_URL = os.getenv("PROBE_DETECTOR_URL", "http://localhost:8020")
CORRELATOR_URL = os.getenv("PROBE_CORRELATOR_URL", "http://localhost:8021")

POLL_INTERVAL_SECONDS = 5
DIAGNOSIS_TIMEOUT_SECONDS = 90
SETTLE_SECONDS = 5  # let the fault actually manifest in telemetry before polling


def read_flags(client: httpx.Client) -> dict:
    response = client.get(f"{FLAGD_UI_URL}/api/read")
    response.raise_for_status()
    return response.json()


def write_flags(client: httpx.Client, flags_config: dict):
    response = client.post(f"{FLAGD_UI_URL}/api/write", json={"data": flags_config})
    response.raise_for_status()


def set_flag_variant(client: httpx.Client, flag_name: str, variant: str):
    config = read_flags(client)
    config["flags"][flag_name]["defaultVariant"] = variant
    write_flags(client, config)


def scan_for_anomalies(client: httpx.Client) -> list[dict]:
    response = client.post(f"{DETECTOR_URL}/scan", timeout=30.0)
    response.raise_for_status()
    return response.json()["anomalies"]


def correlate(client: httpx.Client, anomalies: list[dict]) -> dict:
    response = client.post(f"{CORRELATOR_URL}/correlate", json={"anomalies": anomalies}, timeout=60.0)
    response.raise_for_status()
    return response.json()


def threshold_baseline_alert(anomalies: list[dict], error_rate_threshold: float) -> list[str]:
    """Deliberately dumb: fires on any service whose trace error rate anomaly
    exceeds a fixed threshold. Never names a root cause, just symptoms."""
    return [
        a["service"]
        for a in anomalies
        if a["signal_type"] == "trace_error_rate" and a["current"] >= error_rate_threshold
    ]


def wait_for_diagnosis(client: httpx.Client) -> tuple[dict | None, list[dict]]:
    deadline = time.monotonic() + DIAGNOSIS_TIMEOUT_SECONDS
    last_anomalies: list[dict] = []
    while time.monotonic() < deadline:
        last_anomalies = scan_for_anomalies(client)
        if last_anomalies:
            diagnosis = correlate(client, last_anomalies)
            if diagnosis.get("root_cause_service"):
                return diagnosis, last_anomalies
        time.sleep(POLL_INTERVAL_SECONDS)
    return None, last_anomalies


def run_fault(client: httpx.Client, fault: dict, error_rate_threshold: float) -> dict:
    flag_name = fault["flagd_flag"]
    log.info("Injecting %s = %s", flag_name, fault["inject_variant"])
    set_flag_variant(client, flag_name, fault["inject_variant"])
    t0 = time.monotonic()

    try:
        time.sleep(SETTLE_SECONDS)
        diagnosis, anomalies = wait_for_diagnosis(client)
        latency = time.monotonic() - t0

        correct = bool(
            diagnosis
            and diagnosis.get("root_cause_service") == fault["expected_root_cause_service"]
            and diagnosis.get("root_cause_signal") == fault["expected_signal"]
        )
        baseline_alerts = threshold_baseline_alert(anomalies, error_rate_threshold)

        result = {
            "flagd_flag": flag_name,
            "expected_root_cause_service": fault["expected_root_cause_service"],
            "expected_signal": fault["expected_signal"],
            "diagnosis": diagnosis,
            "correct": correct,
            "latency_seconds": round(latency, 1),
            "baseline_alerted_services": baseline_alerts,
            "baseline_named_root_cause": False,  # by design, the threshold baseline never names a cause
        }
        status = "CORRECT" if correct else "WRONG"
        log.info("%s: %s in %.1fs (diagnosed=%s)", flag_name, status, latency, diagnosis)
        return result
    finally:
        log.info("Resetting %s = %s", flag_name, fault["reset_variant"])
        set_flag_variant(client, flag_name, fault["reset_variant"])


def main():
    config = yaml.safe_load(FAULTS_PATH.read_text())
    faults = config["faults"]
    error_rate_threshold = config["threshold_baseline"]["error_rate_threshold"]

    run_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    RESULTS_DIR.mkdir(exist_ok=True)
    results_path = RESULTS_DIR / f"{run_id}.json"

    results = []
    with httpx.Client() as client:
        for fault in faults:
            results.append(run_fault(client, fault, error_rate_threshold))

    correct_count = sum(1 for r in results if r["correct"])
    latencies = [r["latency_seconds"] for r in results if r["diagnosis"]]
    mean_latency = sum(latencies) / len(latencies) if latencies else float("nan")
    baseline_named_cause_count = sum(1 for r in results if r["baseline_named_root_cause"])
    baseline_fired_count = sum(1 for r in results if r["baseline_alerted_services"])

    summary = {
        "run_id": run_id,
        "total_faults": len(results),
        "probe_correct": correct_count,
        "probe_mean_latency_seconds": round(mean_latency, 1) if latencies else None,
        "baseline_fired_count": baseline_fired_count,
        "baseline_named_root_cause_count": baseline_named_cause_count,
        "results": results,
    }
    results_path.write_text(json.dumps(summary, indent=2, default=str))

    print()
    print("=" * 60)
    print(f"PROBE: root-caused {correct_count}/{len(results)} at mean {summary['probe_mean_latency_seconds']}s")
    print(f"Baseline: fired on {baseline_fired_count}/{len(results)}, "
          f"named the cause on {baseline_named_cause_count}/{len(results)}")
    print(f"Full results: {results_path}")
    print("=" * 60)

    return 0 if correct_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
