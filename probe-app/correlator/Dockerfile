# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY correlator/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY correlator/src src
COPY correlator/run.py .

EXPOSE ${PROBE_CORRELATOR_PORT}

CMD ["python", "run.py"]
