#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Thin ES|QL query helper.

Uses ELASTIC_API_KEY_READ (a read+monitor scoped key — see .env.override),
never the ingest-only ELASTIC_OTLP_API_KEY used by the collector.
"""

import os

from elasticsearch import Elasticsearch


class ESClient:
    def __init__(self):
        self._es = Elasticsearch(
            os.environ["ELASTIC_ES_URL"],
            api_key=os.environ["ELASTIC_API_KEY_READ"],
        )

    def esql_rows(self, query: str) -> list[dict]:
        """Run an ES|QL query and return rows as a list of {column: value} dicts."""
        response = self._es.esql.query(query=query)
        columns = [c["name"] for c in response["columns"]]
        return [dict(zip(columns, row)) for row in response["values"]]
