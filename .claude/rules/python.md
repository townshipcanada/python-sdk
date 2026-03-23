---
description: Python conventions for this SDK
globs: "*.py"
---

- Use `from __future__ import annotations` in every module
- Type-hint all public functions, methods, and class attributes
- Use Pydantic v2 models (BaseModel) for data structures
- Use httpx for HTTP requests (not requests/urllib)
- Coordinates follow GeoJSON: `[longitude, latitude]`
- Custom exceptions inherit from `TownshipCanadaError`
- Test with pytest + respx mocking; use `pytest.mark.asyncio` for async tests
- Batch operations must chunk at 100 items max
