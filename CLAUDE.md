# CLAUDE.md

# PyIngestKit — Claude Code & Interactive Agent Instructions

This file contains operational instructions for Claude Code, Antigravity, and interactive coding sessions.
It is intentionally a thin overlay. The canonical repository-wide instructions live in:

```text
AGENTS.md
```

Agents MUST read and follow `AGENTS.md` before making changes.

Authority order:
```text
specifications / fixtures / tests
        ↓
AGENTS.md
        ↓
CLAUDE.md
```

---

## 1. First Action in Every Coding Session (Pre-Flight Protocol)

Before editing code:
```text
1. Read AGENTS.md.
2. Check git status and current branch (git status -sb).
3. Confirm version in src/pyingestkit/_version.py and pyproject.toml.
4. Inspect the relevant RFC, release note, or implementation plan in docs/.
5. Inspect adjacent test suites and contract fixtures in tests/contract/fixtures/.
6. Plan changes strictly respecting the frozen 2.x root and RFC-001 invariants.
```

The live repository is the source of truth. Never assume state from memory or stale notes.

---

## 2. Preferred Test & Development Cycle

```text
inspect
  → implement small, coherent change
  → run targeted test: pytest -q tests/unit/v2/test_<target>.py
  → fix and refine
  → run architecture check: make architecture-v2
  → run full baseline: make check-v2
  → check style and types: make quality
```

Do not defer all verification to the end of the session.

---

## 3. Standard Commands Cheatsheet

```bash
# Targeted testing
pytest tests/unit/v2/test_<name>.py -v
pytest tests/architecture/ -v
pytest tests/contract/public_api/ -v

# Global quality checks
make architecture-v2  # Architecture boundary validation
make contract-v2      # Public API and contract freeze validation
make check-v2         # Full V2 test suite
make quality          # Ruff check + format check + Mypy strict
make security         # Bandit + pip-audit
make verify           # check-v2 + quality + security + build

# Documentation
make docs-build       # mkdocs build --strict
make docs-serve       # mkdocs serve
```

---

## 4. Prohibited Actions for Agents

- **DO NOT** add new exports to `pyingestkit/__init__.py` without an accepted RFC.
- **DO NOT** reintroduce `Job`, `Pipeline`, `Step`, or `Runner` in V2 code.
- **DO NOT** edit JSON files under `tests/contract/fixtures/` to fix test failures.
- **DO NOT** bypass Compare-and-Swap in conditional publishers.
- **DO NOT** add top-level imports of physical drivers (`psycopg`, `boto3`, `httpx`) in core or domain modules.
