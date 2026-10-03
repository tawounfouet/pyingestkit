# Customer 360 — PyIngestKit LOT-20 local reference profile

This example is executable architecture evidence for the PyIngestKit portions of
the ecosystem Customer 360 reference application.

It proves:

- customers CSV ingestion with durable RAW;
- orders CSV ingestion with durable RAW;
- source DatasetVersion storage and publication;
- portable DatasetVersionReference handoff through the official PyTransformKit ACL;
- resource-backed Customer 360 transformation on Pandas or Polars;
- physical transformation write remaining distinct from PyIngestKit publication;
- customer_mart promotion into a governed DatasetVersion;
- traversable source-version/artifact and transformation provenance;
- strict source replay from preserved RAW with a new IngestionRunId.

The uncertainty/reconciliation and security-negative scenarios are qualified by
the LOT-20 test suite rather than hidden inside the happy-path runner.

The runner intentionally uses qualified V2 transition namespaces because the
package root remains frozen for the maintained V1 line until the 2.0 package cut.
