#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Picks the Correlator's LLM backend from LLM_PROVIDER. Defaults to
Bedrock (the real path for the actual hackathon submission); "anthropic",
"openai", and "gemini" are dev/testing stand-ins that only need an API
key, no AWS account — see bedrock_client.py / anthropic_client.py /
openai_client.py / gemini_client.py."""

import os


def get_correlator():
    provider = os.getenv("LLM_PROVIDER", "bedrock").lower()
    if provider == "bedrock":
        from src.correlator.bedrock_client import BedrockCorrelator

        return BedrockCorrelator()
    if provider == "anthropic":
        from src.correlator.anthropic_client import AnthropicCorrelator

        return AnthropicCorrelator()
    if provider == "openai":
        from src.correlator.openai_client import OpenAICorrelator

        return OpenAICorrelator()
    if provider == "gemini":
        from src.correlator.gemini_client import GeminiCorrelator

        return GeminiCorrelator()
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (expected bedrock, anthropic, openai, or gemini)")
