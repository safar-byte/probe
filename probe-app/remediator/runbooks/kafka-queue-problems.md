---
fault_signature: kafkaQueueProblems
service: kafka
title: Kafka queue overloaded, consumers lagging
---
`kafkaQueueProblems` overloads the Kafka queue, causing consumer lag in
downstream services (fraud-detection, accounting). Expect anomalies to
appear first/most strongly in kafka's own metrics, with fraud-detection
and accounting showing lag or processing-delay symptoms. Fix: disable the
flag, or scale Kafka/consumers if this occurs organically.
