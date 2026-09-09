---
fault_signature: adManualGc
service: ad
title: Ad service forcing GC pauses
---
The `adManualGc` flag forces manual garbage collection in the ad service,
causing periodic latency spikes rather than a sustained slowdown. Fix:
disable `adManualGc`; in a real incident, check JVM GC logs/heap pressure.
