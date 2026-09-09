---
fault_signature: emailMemoryLeak
service: email
title: Email service leaking memory
---
`emailMemoryLeak` multiplies memory retained per request in the email
service, degrading it over time (slower responses, eventual OOM/restart)
rather than failing immediately — expect the anomaly to build gradually
rather than spike. Fix: disable the flag, or restart/profile the email
service for a real leak.
