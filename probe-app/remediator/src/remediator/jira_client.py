#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Secondary ticket output — a real Jira issue. Deliberately isolated from
the Kibana Case path: if Jira is unreachable or misconfigured, this must
fail without breaking the primary (Kibana Case) path or the live demo."""

import base64
import os

import httpx


def jira_configured() -> bool:
    return bool(os.getenv("JIRA_BASE_URL") and os.getenv("JIRA_EMAIL") and os.getenv("JIRA_API_TOKEN"))


class JiraClient:
    def __init__(self):
        self._base_url = os.environ["JIRA_BASE_URL"].rstrip("/")
        self._project_key = os.environ["JIRA_PROJECT_KEY"]
        token = base64.b64encode(
            f"{os.environ['JIRA_EMAIL']}:{os.environ['JIRA_API_TOKEN']}".encode()
        ).decode()
        self._auth_header = f"Basic {token}"

    def create_issue(self, diagnosis: dict, runbook: dict | None) -> dict:
        summary = f"PROBE: {diagnosis['root_cause_service']} — {diagnosis['root_cause_signal']}"
        description = diagnosis["reasoning"]
        if runbook:
            description += f"\n\nSuggested fix ({runbook['title']}):\n{runbook['body']}"

        response = httpx.post(
            f"{self._base_url}/rest/api/3/issue",
            headers={"Authorization": self._auth_header, "Content-Type": "application/json"},
            json={
                "fields": {
                    "project": {"key": self._project_key},
                    "summary": summary,
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text": description}]}
                        ],
                    },
                    "issuetype": {"name": "Bug"},
                    "labels": ["probe", diagnosis["root_cause_service"]],
                }
            },
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()
