---
fault_signature: cartFailure
service: cart
title: Cart service failing a percentage of requests
---
`cartFailure` routes a configured percentage of cart operations to a
broken cart store, so failures are probabilistic rather than total.
Anything that calls cart (frontend, checkout) will show a proportional
error rate. Fix: disable `cartFailure`, or investigate the real cart
store/Valkey connection if this occurs without the flag.
