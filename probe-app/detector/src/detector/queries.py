#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""ES|QL query shapes over Elastic's OTel-native data streams.

Data lands as traces-*.otel-default / metrics-*.otel-default /
logs-*.otel-default (confirmed via src/otel-collector/otelcol-elastic-config.yaml,
which exports through Elastic's native OTLP intake, not the classic
`elasticsearch` exporter with a manual traces-apm-default style mapping).

Each query buckets a signal by service.name over WINDOW in BUCKET-sized
steps. The last bucket is "recent"; everything before it is "baseline" —
the caller (anomaly.py) compares the two per service.

Every query excludes service.name LIKE "probe-*" — PROBE's own services
(this Detector included) must never be candidates for "the incident",
even as defense-in-depth on top of not self-exporting telemetry into this
project (see run.py — self-instrumentation was removed on purpose so
astronomy-shop-elastic's telemetry stays exclusively about the shop).
"""

WINDOW = "5 minutes"
BUCKET = "30 seconds"

_EXCLUDE_PROBE = 'NOT service.name LIKE "probe-*"'


def error_rate_by_service() -> str:
    return f"""
FROM traces-*.otel-default
| WHERE @timestamp > NOW() - {WINDOW} AND {_EXCLUDE_PROBE}
| EVAL is_error = CASE(status.code == "Error", 1, 0)
| STATS error_rate = AVG(is_error), total = COUNT(*)
    BY service.name, bucket = BUCKET(@timestamp, {BUCKET})
| SORT service.name, bucket
"""


def latency_p95_by_service() -> str:
    return f"""
FROM traces-*.otel-default
| WHERE @timestamp > NOW() - {WINDOW} AND {_EXCLUDE_PROBE}
| STATS p95_ns = PERCENTILE(duration, 95), total = COUNT(*)
    BY service.name, bucket = BUCKET(@timestamp, {BUCKET})
| SORT service.name, bucket
"""


def log_error_burst_by_service() -> str:
    return f"""
FROM logs-*.otel-default
| WHERE @timestamp > NOW() - {WINDOW} AND severity_text IN ("ERROR", "FATAL")
    AND NOT resource.attributes.service.name LIKE "probe-*"
| STATS error_count = COUNT(*)
    BY service.name = resource.attributes.service.name, bucket = BUCKET(@timestamp, {BUCKET})
| SORT service.name, bucket
"""
