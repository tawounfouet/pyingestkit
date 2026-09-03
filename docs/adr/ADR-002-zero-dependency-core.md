# ADR-002 — Zero third-party dependency core

**Status:** Superseded by ADR-010  
**Date:** 2026-09-03

## Historical decision

The initial PyIngestKit architecture proposed a stdlib-only core to minimize dependency surface and avoid coupling the ingestion runtime to infrastructure libraries.

## Superseded

This constraint was intentionally removed in V0.1.2.

PyIngestKit is an industrial Python framework, and selected third-party packages are acceptable when they provide a strong, maintained, production-grade contract and remove low-value custom infrastructure code.

See **ADR-010 — Production-grade dependency policy**.
