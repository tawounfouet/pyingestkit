# ADR-006 — Atomic publication semantics

**Status:** Accepted for V0.1

## Decision

A candidate is promoted with all-or-nothing filesystem semantics using a temporary file and atomic replace on the destination filesystem.
