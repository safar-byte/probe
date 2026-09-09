---
fault_signature: intlShippingSlowdown
service: shipping
title: International shipping quotes responding slowly
---
`intlShippingSlowdown` delays shipping-quote responses for international
addresses only, so the anomaly may be partial/intermittent depending on
traffic mix rather than affecting every request. Fix: disable the flag,
or investigate the shipping/quote service's international rate lookup.
