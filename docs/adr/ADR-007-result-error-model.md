# ADR-007 — Result and error model

**Status:** Accepted for V0.1

## Decision

Successful execution yields SUCCESS results. Failures raise exceptions at the operation boundary and the runtime records them as FAILED results. No success=true/error-in-payload ambiguity.
