#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Primary ticket output — a Kibana Case. Stays inside Elastic, no extra
external credential, and must succeed reliably for the live demo."""

import os

import httpx


class KibanaCaseClient:
    def __init__(self):
        self._base_url = os.environ["KIBANA_URL"].rstrip("/")
        self._api_key = os.environ["ELASTIC_API_KEY_READ"]

    def create_case(self, diagnosis: dict, runbook: dict | None) -> dict:
        title = f"PROBE: {diagnosis['root_cause_service']} — {diagnosis['root_cause_signal']}"
        description = diagnosis["reasoning"]
        if runbook:
            description += f"\n\nSuggested fix ({runbook['title']}):\n{runbook['body']}"

        response = httpx.post(
            f"{self._base_url}/api/cases",
            headers={
                "Authorization": f"ApiKey {self._api_key}",
                "kbn-xsrf": "true",
                "Content-Type": "application/json",
            },
            json={
                "title": title,
                "description": description,
                "tags": ["probe", diagnosis["root_cause_service"]],
                "connector": {"id": "none", "name": "none", "type": ".none", "fields": None},
                "settings": {"syncAlerts": False},
                "owner": "observability",
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()
