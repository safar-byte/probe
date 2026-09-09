---
fault_signature: adHighCpu
service: ad
title: Ad service pegged at high CPU, increasing latency
---
The `adHighCpu` flag makes the ad service burn CPU on every request,
increasing its own latency and, transitively, the latency of anything
waiting on it (frontend). Fix: disable `adHighCpu`, or scale/profile the
ad service if this is organic load rather than an injected fault.
