#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""GPT via the OpenAI API directly — the other dev/testing stand-in for
Bedrock, for whichever API key you have on hand. Same tool-forced-JSON
approach and shared prompt/schema as the other two backends."""

import json
import os

from openai import OpenAI

from src.correlator.diagnosis_schema import (
    DIAGNOSIS_JSON_SCHEMA,
    SYSTEM_PROMPT,
    TOOL_DESCRIPTION,
    TOOL_NAME,
    user_content,
)


class OpenAICorrelator:
    def __init__(self):
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def diagnose(self, anomalies: list[dict], dependency_graph: dict) -> dict:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content(anomalies, dependency_graph)},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": TOOL_NAME,
                        "description": TOOL_DESCRIPTION,
                        "parameters": DIAGNOSIS_JSON_SCHEMA,
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
        )
        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise RuntimeError("OpenAI response did not include a report_diagnosis tool call")
        return json.loads(tool_calls[0].function.arguments)
