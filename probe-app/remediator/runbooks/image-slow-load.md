---
fault_signature: imageSlowLoad
service: frontend
title: Frontend product images loading slowly
---
`imageSlowLoad` adds artificial delay to frontend image loading. This
shows up as elevated frontend latency without a corresponding backend
service anomaly — a useful case for distinguishing "root cause is
frontend itself" from "root cause is a backend dependency". Fix: disable
`imageSlowLoad`.
