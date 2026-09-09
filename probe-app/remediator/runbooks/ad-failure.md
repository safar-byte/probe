---
fault_signature: adFailure
service: ad
title: Ad service throwing errors on every request
---
The ad service's `adFailure` feature flag is forcing every ad request to
throw. Symptom services (frontend, checkout) will show elevated error
rates purely from waiting on/handling failed ad calls, not from their own
code. Fix: disable the `adFailure` flag in flagd, or roll back the ad
service deployment if the flag isn't the cause in a real incident.
