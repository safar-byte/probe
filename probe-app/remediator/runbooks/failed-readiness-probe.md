---
fault_signature: failedReadinessProbe
service: cart
title: Cart readiness probe failing
---
`failedReadinessProbe` makes the cart service's readiness endpoint report
unready, which can cause the orchestrator to stop routing traffic to it
or restart it, producing connection-refused/timeout symptoms in callers.
Fix: disable the flag; in a real incident check the cart service's actual
startup dependencies (Valkey, product-catalog).
