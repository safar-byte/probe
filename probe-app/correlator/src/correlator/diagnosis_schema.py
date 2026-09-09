#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Shared system prompt + tool JSON schema for all three LLM backends
(Bedrock, Anthropic direct, OpenAI direct) — see llm_client.py. Kept in one
place so switching LLM_PROVIDER can never drift the three prompts apart."""

TOOL_NAME = "report_diagnosis"
TOOL_DESCRIPTION = "Report the single root-cause service and signal for this incident."

DIAGNOSIS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause_service": {
            "type": "string",
            "description": "The one service whose anomaly caused the incident.",
        },
        "root_cause_signal": {
            "type": "string",
            "description": "The specific signal/metric that identifies the cause (e.g. trace_error_rate, trace_latency_p95, log_error_burst).",
        },
        "confidence": {
            "type": "number",
            "description": "0.0-1.0 confidence in this diagnosis.",
        },
        "reasoning": {
            "type": "string",
            "description": "Why this anomaly is the cause and the others are downstream symptoms, referencing the dependency graph.",
        },
        "symptom_services": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Other anomalous services that are knock-on symptoms, not the cause.",
        },
    },
    "required": ["root_cause_service", "root_cause_signal", "confidence", "reasoning", "symptom_services"],
}

SYSTEM_PROMPT = """You are the Correlator in PROBE, an incident root-cause diagnosis system.

You are given:
1. A service dependency graph (caller -> [callees]) for a microservices e-commerce demo.
2. A list of anomalies detected across traces, metrics, and logs in the last few minutes.

Most of these anomalies are knock-on symptoms: when one service fails, every service
that calls it (directly or transitively) also starts showing elevated error rates or
latency, even though it is functioning correctly itself. Your job is to reason through
the dependency graph and identify the SINGLE service and signal that is the true root
cause — the one anomaly that, if fixed, would resolve all the others.

Prefer the anomaly in the service that is deepest in the call chain among the anomalous
services (i.e. called by other anomalous services, but not itself calling another
anomalous service) unless the evidence clearly points elsewhere.

Always respond by calling the report_diagnosis tool exactly once."""


def user_content(anomalies: list, dependency_graph: dict) -> str:
    import json

    return (
        f"Dependency graph:\n{json.dumps(dependency_graph, indent=2)}\n\n"
        f"Detected anomalies:\n{json.dumps(anomalies, indent=2)}"
    )
