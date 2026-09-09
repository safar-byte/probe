---
fault_signature: paymentFailure
service: payment
title: Payment service failing a percentage of charges
---
`paymentFailure` throws for a configured percentage of charge attempts
(see src/payment/charge.js). Checkout will show a proportional error
rate purely as a consequence. Fix: disable `paymentFailure`, or check the
real payment processor/card-validation logic if unflagged.
