# Security Policy

PyIngestKit V0.1 follows these rules:

- secrets are not artifacts;
- secrets must not be written to manifests;
- the library does not configure global logging handlers at import time;
- importing `pyingestkit` must not create files, open connections, or discover plugins;
- plugins are discovered only when explicitly requested;
- run artifacts should contain data/provenance only, never credentials.

Report security issues privately to the project maintainer rather than opening a public issue containing secrets.
