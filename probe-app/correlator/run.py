#!/usr/bin/python

# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging

from dotenv import load_dotenv
from src.correlator.service import Correlator

logging.basicConfig(level=logging.INFO)

load_dotenv()


async def start_servers():
    correlator = Correlator()
    await correlator.launch()


if __name__ == "__main__":
    try:
        asyncio.run(start_servers())
    except KeyboardInterrupt:
        logging.info("Shutting down probe-correlator...")
