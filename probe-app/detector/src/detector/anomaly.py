#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

"""Client-side z-score anomaly scoring over ES|QL bucketed rows.

ES|QL's CHANGE_POINT command may not be available on every Elastic
Serverless project tier — verify at Stage 0/1 start. This z-score fallback
works regardless of tier, so it's the default rather than an afterthought.
"""

from collections import defaultdict
from statistics import mean, stdev

Z_SCORE_THRESHOLD = 3.0


def score_anomalies(rows: list[dict], value_field: str, signal_type: str, metric_name: str) -> list[dict]:
    """Group rows by service.name, split the window into an earlier baseline
    half and a recent second half, and return anomalies whose z-score
    exceeds the threshold.

    Splitting in half (rather than "everything but the single last bucket")
    matters once a fault has been active for more than one bucket: with a
    single-bucket "recent" window, buckets 2+ after injection start
    polluting their own baseline (they'd already be counted as history),
    which dilutes the z-score right when the signal is strongest. A fixed
    earlier/later split keeps the baseline half clean of the fault for as
    long as it's been active for less than half the total window.
    """
    by_service = defaultdict(list)
    for row in rows:
        service = row.get("service.name")
        value = row.get(value_field)
        bucket = row.get("bucket")
        if service is None or value is None or bucket is None:
            continue
        by_service[service].append((bucket, value))

    anomalies = []
    for service, points in by_service.items():
        points.sort(key=lambda p: p[0])
        if len(points) < 4:
            continue  # not enough history to judge a baseline
        split = len(points) // 2
        baseline_points, recent_points = points[:split], points[split:]
        baseline_values = [v for _, v in baseline_points]
        recent_values = [v for _, v in recent_points]
        recent_bucket = recent_points[-1][0]
        recent_value = mean(recent_values)
        baseline_mean = mean(baseline_values)
        try:
            baseline_stdev = stdev(baseline_values)
        except (ValueError, ArithmeticError):
            baseline_stdev = 0.0

        if baseline_stdev > 0:
            z_score = (recent_value - baseline_mean) / baseline_stdev
        elif recent_value > baseline_mean:
            z_score = Z_SCORE_THRESHOLD + 1  # baseline was flat, recent value isn't
        else:
            z_score = 0.0

        if z_score >= Z_SCORE_THRESHOLD:
            anomalies.append(
                {
                    "service": service,
                    "signal_type": signal_type,
                    "metric": metric_name,
                    "baseline": round(baseline_mean, 4),
                    "current": round(recent_value, 4),
                    "deviation_score": round(z_score, 2),
                    "window": str(recent_bucket),
                }
            )
    return anomalies
