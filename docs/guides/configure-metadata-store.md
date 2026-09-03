# Configure MetadataStore

SQLite is the default and resolves to `<workspace>/state/pyingest.sqlite3` unless an explicit path is configured. PostgreSQL uses a DSN environment variable; do not version a DSN containing credentials.
