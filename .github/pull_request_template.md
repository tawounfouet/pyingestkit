## Summary
Description concise du changement et du comportement introduit ou modifié.

## Architecture Impact (RFC-001 & Invariants V2)
- Quelle responsabilité PyIngestKit ce changement concerne-t-il ?
- Affecte-t-il un invariant de gouvernance (Compare-and-Swap, Ledgers durables, Holds, GC sécurisé, Governed Rollback) ?
- Traverse-t-il une frontière Domain / Port / Adapter ?

## Compatibility & Contract Checklist
- [ ] Root public API (`from pyingestkit import ...`) : aucune rupture
- [ ] Qualified governance namespaces (`pyingestkit.governance.*`) : conforme
- [ ] Schéma de persistance PostgreSQL (`schema_version = 1`) : inchangé ou migration fournie
- [ ] Boundary wire contracts / sérialisation (`tests/contract/fixtures/`) : conforme
- [ ] Compatibilité 1.x / V1 migration : préservée
- [ ] Aucun changement de contrat non documenté

## Verification Checklist
- [ ] Tests unitaires V2 (`tests/unit/v2`)
- [ ] Tests d'architecture (`tests/architecture`)
- [ ] Tests de conformité des connecteurs (`tests/conformance/v2`)
- [ ] Tests d'intégration multi-providers (`tests/integration/v2`)
- [ ] Qualité & Typage (`make quality`)
- [ ] Sécurité (`make security`)
- [ ] Build & Smoke Wheel (`make verify`)

## Notes
Considérations de migration, limitations connues ou travaux reportés.
