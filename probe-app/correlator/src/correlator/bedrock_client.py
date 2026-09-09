#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Claude on Amazon Bedrock via the Converse API.

boto3 + Converse (not LangChain's ChatBedrock, not a LangGraph ReAct loop
like src/agent uses) — this is deliberately single-shot structured
reasoning over a fixed input, so the simpler surface is the right one:
fewer moving parts to debug live, and the self-grading harness needs a
reliable JSON field to diff against ground truth, not free text to parse.
Bedrock tool-use is used purely to force that structured output.
"""

import os

import boto3

from src.correlator.diagnosis_schema import (
    DIAGNOSIS_JSON_SCHEMA,
    SYSTEM_PROMPT,
    TOOL_DESCRIPTION,
    TOOL_NAME,
    user_content,
)

_REPORT_DIAGNOSIS_TOOL = {
    "toolSpec": {
        "name": TOOL_NAME,
        "description": TOOL_DESCRIPTION,
        "inputSchema": {"json": DIAGNOSIS_JSON_SCHEMA},
    }
}


class BedrockCorrelator:
    def __init__(self):
        self._client = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
        self._model_id = os.environ["BEDROCK_MODEL_ID"]

    def diagnose(self, anomalies: list[dict], dependency_graph: dict) -> dict:
        response = self._client.converse(
            modelId=self._model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": user_content(anomalies, dependency_graph)}]}],
            toolConfig={
                "tools": [_REPORT_DIAGNOSIS_TOOL],
                "toolChoice": {"tool": {"name": TOOL_NAME}},
            },
        )
        for block in response["output"]["message"]["content"]:
            if "toolUse" in block:
                return block["toolUse"]["input"]
        raise RuntimeError("Bedrock response did not include a report_diagnosis tool call")
