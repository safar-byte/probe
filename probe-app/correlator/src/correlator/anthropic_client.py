#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Claude via the Anthropic API directly — a dev/testing stand-in for
Bedrock that only needs an Anthropic API key, no AWS account/IAM setup.
Same tool-forced-JSON approach as bedrock_client.py, same prompt/schema
(diagnosis_schema.py), so swapping LLM_PROVIDER changes nothing about the
Correlator's behavior — only which API answers the call."""

import os

import anthropic

from src.correlator.diagnosis_schema import (
    DIAGNOSIS_JSON_SCHEMA,
    SYSTEM_PROMPT,
    TOOL_DESCRIPTION,
    TOOL_NAME,
    user_content,
)


class AnthropicCorrelator:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self._model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")

    def diagnose(self, anomalies: list[dict], dependency_graph: dict) -> dict:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content(anomalies, dependency_graph)}],
            tools=[{"name": TOOL_NAME, "description": TOOL_DESCRIPTION, "input_schema": DIAGNOSIS_JSON_SCHEMA}],
            tool_choice={"type": "tool", "name": TOOL_NAME},
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
        raise RuntimeError("Anthropic response did not include a report_diagnosis tool call")
