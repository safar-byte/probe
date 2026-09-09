---
fault_signature: paymentUnreachable
service: payment
title: Payment service completely unreachable
---
`paymentUnreachable` makes payment fail every request (not probabilistic,
unlike paymentFailure) — expect a hard, total failure signature rather
than a partial error rate. Fix: disable `paymentUnreachable`, or check
network/DNS/service health if this occurs without the flag.
