# Township Canada Python SDK

Python SDK for the Township Canada land survey API. Provides sync/async clients, Pydantic models, and a CLI.

## Build & Test

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Build distribution
python -m build
```

## Project Structure

- `townshipcanada/` — Package source (client, models, exceptions, CLI)
- `tests/test_client.py` — Tests (pytest + respx for HTTP mocking + pytest-asyncio)
- `.github/workflows/` — CI (ci.yml) and PyPI publish (publish.yml)

## Conventions

- Python 3.9+ compatibility (`from __future__ import annotations`)
- Type hints on all public APIs; `py.typed` marker present
- Pydantic v2 for models and validation
- httpx for HTTP (sync + async)
- GeoJSON coordinates are `[longitude, latitude]`

## Verification

Before claiming any task complete, run:

```bash
pytest tests/ -v
```

All tests must pass. If adding new functionality, add corresponding tests in `tests/test_client.py`.
