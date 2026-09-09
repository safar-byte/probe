#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Gemini via the Google AI (Gemini Developer API) directly — another
dev/testing stand-in for Bedrock. Same shared prompt/schema as the other
three backends (diagnosis_schema.py); the one wrinkle is that Gemini's
function-calling schema uses uppercase OpenAPI-style type names (STRING,
OBJECT, ARRAY, ...) rather than JSON Schema's lowercase ones, hence
_to_gemini_schema below."""

import os

import google.generativeai as genai

from src.correlator.diagnosis_schema import (
    DIAGNOSIS_JSON_SCHEMA,
    SYSTEM_PROMPT,
    TOOL_DESCRIPTION,
    TOOL_NAME,
    user_content,
)


def _to_python(value):
    """Recursively convert a protobuf Struct/MapComposite/RepeatedComposite
    (what function_call.args actually is) into plain dict/list/scalars —
    dict(fc.args) alone only converts the top level, leaving nested fields
    (e.g. the symptom_services array) as protobuf types FastAPI can't
    JSON-serialize."""
    if hasattr(value, "items"):
        return {k: _to_python(v) for k, v in value.items()}
    if hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
        return [_to_python(v) for v in value]
    return value


def _to_gemini_schema(schema: dict) -> dict:
    converted = {"type": schema["type"].upper()}
    if "description" in schema:
        converted["description"] = schema["description"]
    if "properties" in schema:
        converted["properties"] = {k: _to_gemini_schema(v) for k, v in schema["properties"].items()}
    if "items" in schema:
        converted["items"] = _to_gemini_schema(schema["items"])
    if "required" in schema:
        converted["required"] = schema["required"]
    return converted


class GeminiCorrelator:
    def __init__(self):
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self._model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
            system_instruction=SYSTEM_PROMPT,
            tools=[
                {
                    "function_declarations": [
                        {
                            "name": TOOL_NAME,
                            "description": TOOL_DESCRIPTION,
                            "parameters": _to_gemini_schema(DIAGNOSIS_JSON_SCHEMA),
                        }
                    ]
                }
            ],
            tool_config={"function_calling_config": {"mode": "ANY", "allowed_function_names": [TOOL_NAME]}},
        )

    def diagnose(self, anomalies: list[dict], dependency_graph: dict) -> dict:
        response = self._model.generate_content(user_content(anomalies, dependency_graph))
        for part in response.candidates[0].content.parts:
            fc = getattr(part, "function_call", None)
            if fc and fc.name == TOOL_NAME:
                return _to_python(fc.args)
        raise RuntimeError("Gemini response did not include a report_diagnosis function call")
