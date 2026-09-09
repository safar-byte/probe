---
fault_signature: productCatalogFailure
service: product-catalog
title: Product catalog failing for a specific product
---
`productCatalogFailure` is targeted via a `product_id` rule rather than
affecting the whole service — expect the anomaly to be narrower/lower
volume than a full-service outage, and correlated with requests for one
specific product. Fix: disable the targeting rule, or investigate that
product's catalog entry if unflagged.
