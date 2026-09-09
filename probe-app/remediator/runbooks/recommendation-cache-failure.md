---
fault_signature: recommendationCacheFailure
service: recommendation
title: Recommendation service cache failing
---
`recommendationCacheFailure` breaks the recommendation service's cache,
increasing its own latency (cache misses falling through to a slower
path) without necessarily erroring. Fix: disable the flag, or check the
real cache backend if this occurs without it.
