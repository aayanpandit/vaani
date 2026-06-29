# Vaani

> Production-grade AI project built with modern Python tooling.

## Overview

**Vaani** is structured for maintainability, type-safety, and reproducibility,
following current Python engineering best practices. This repository contains
the engineering foundation — tooling, CI, and project configuration — for the
Vaani codebase.

## Tech Stack

| Concern              | Tool                |
|-----------------------|----------------------|
| Language              | Python 3.12+         |
| Package management     | [uv](https://docs.astral.sh/uv/) |
| Linting                | [Ruff](https://docs.astral.sh/ruff/) |
| Formatting             | Ruff format / Black   |
| Import sorting         | isort                |
| Static typing          | MyPy (strict mode)    |
| Testing                | pytest + pytest-cov   |
| Git hooks              | pre-commit            |
| CI/CD                  | GitHub Actions        |
| Commit convention      | Conventional Commits  |

## Project Structure

```
vaani/
├── src/
│   └── vaani/              # Application source code
├── tests/                  # Test suite
├── .github/
│   └── workflows/
│       └── ci.yml          # CI pipeline
├── pyproject.toml          # Project & tool configuration
├── .pre-commit-config.yaml # Git hook definitions
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Setup

```bash
# Clone the repository
git clone https://github.com/<org>/vaani.git
cd vaani

# Install dependencies (including dev tools)
uv sync --extra dev

# Install pre-commit hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

### Common Commands

| Task                  | Command                              |
|------------------------|----------------------------------------|
| Run tests              | `uv run pytest`                        |
| Lint                   | `uv run ruff check .`                  |
| Format                 | `uv run ruff format .`                 |
| Type check             | `uv run mypy src`                      |
| Run all pre-commit hooks | `uv run pre-commit run --all-files`  |
| Add a dependency        | `uv add <package>`                   |
| Add a dev dependency    | `uv add --dev <package>`             |

## Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/).
Commit messages are validated automatically via pre-commit.

```
<type>(<optional-scope>): <description>

feat(auth): add token refresh flow
fix(api): handle empty response payload
docs: update setup instructions
chore: bump dependency versions
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`.

## CI Pipeline

Every push and pull request triggers:

1. **Lint** — Ruff, Black, isort checks
2. **Type check** — MyPy in strict mode
3. **Test** — pytest across supported Python versions, with coverage
4. **Security** — dependency vulnerability scan (`pip-audit`)

## Security

- Secrets, credentials, and `.env` files are excluded via `.gitignore`.
- `detect-secrets` runs as a pre-commit hook to catch accidental leaks.
- Dependencies are scanned for known vulnerabilities in CI.
- Report security issues privately rather than via public issues.

## License

MIT — see `LICENSE` for details.
