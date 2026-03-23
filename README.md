# Township Canada Python SDK

[![PyPI](https://img.shields.io/pypi/v/townshipcanada)](https://pypi.org/project/townshipcanada/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Convert Canadian legal land descriptions (DLS, NTS, Geographic Townships) to GPS coordinates and back. Covers Alberta, Saskatchewan, Manitoba, British Columbia, and Ontario.

[Documentation](https://townshipcanada.com/api) · [GitHub](https://github.com/townshipcanada/python-sdk) · [PyPI](https://pypi.org/project/townshipcanada/)

## Installation

```bash
pip install townshipcanada
```

## Quick Start

```python
import os

from townshipcanada import TownshipCanada

tc = TownshipCanada(os.environ["TOWNSHIP_CANADA_API_KEY"])

# DLS (Dominion Land Survey) — Alberta, Saskatchewan, Manitoba
result = tc.search("NW-36-42-3-W5")
print(f"{result.latitude}, {result.longitude}")
# 52.123456, -114.654321

# NTS (National Topographic System) — British Columbia
result = tc.search("A-2-F/93-P-8")

# Geographic Townships — Ontario
result = tc.search("Lot 2 Con 4 Osprey")
```

Get an API key at [townshipcanada.com/api](https://townshipcanada.com/api).

## Examples

### 1. Oil & Gas: Convert Well Locations to GPS

```python
from townshipcanada import TownshipCanada

tc = TownshipCanada("your_api_key")

well_locations = [
    "NW-36-42-3-W5",
    "SE-1-50-10-W4",
    "10-14-42-4-W4",
]

# Batch convert all at once (up to 100 per request, auto-chunks larger arrays)
result = tc.batch_search(well_locations)

for item in result.results:
    print(
        f"{item.legal_location} -> "
        f"{item.latitude:.6f}, {item.longitude:.6f} "
        f"({item.province})"
    )
```

### 2. GIS Pipeline: Reverse Geocode Field Coordinates

```python
from townshipcanada import TownshipCanada

tc = TownshipCanada("your_api_key")

# GPS coordinates from a field survey
field_points = [
    (-114.648933, 52.454928),
    (-110.456789, 50.321654),
    (-106.123456, 52.789012),
]

# Batch reverse geocode to legal land descriptions
result = tc.batch_reverse(field_points, unit="Quarter Section")

for item in result.results:
    print(item.legal_location)
```

### 3. Real Estate: Look Up a Single Parcel with GeoPandas

```python
import geopandas as gpd
from shapely.geometry import shape

from townshipcanada import TownshipCanada

tc = TownshipCanada("your_api_key")

result = tc.search("NW-36-42-3-W5")

# Convert the grid boundary to a Shapely geometry
if result.boundary:
    geometry = shape(result.boundary.model_dump())

    gdf = gpd.GeoDataFrame(
        [{"legal_location": result.legal_location, "province": result.province}],
        geometry=[geometry],
        crs="EPSG:4326",
    )

    print(gdf)
    # gdf.to_file("parcel.geojson", driver="GeoJSON")
```

## Async Support

```python
import asyncio

from townshipcanada import AsyncTownshipCanada


async def main():
    async with AsyncTownshipCanada("your_api_key") as tc:
        result = await tc.search("NW-36-42-3-W5")
        print(result.latitude, result.longitude)


asyncio.run(main())
```

## CLI

The SDK includes a command-line tool:

```bash
# Set your API key (TOWNSHIP_API_KEY is also accepted)
export TOWNSHIP_CANADA_API_KEY="your_api_key"

# Convert a legal land description
township convert "NW-36-42-3-W5"
# 52.123456, -114.654321
#   Location:  NW-36-42-3-W5
#   Province:  Alberta
#   System:    DLS
#   Unit:      Quarter Section

# Reverse geocode
township reverse -- -114.654321 52.123456

# JSON output
township convert "NW-36-42-3-W5" --json
```

## API Reference

### `TownshipCanada(api_key, *, base_url=..., timeout=30.0)`

| Method                                                                         | Description                             |
| ------------------------------------------------------------------------------ | --------------------------------------- |
| `search(location)`                                                             | Convert legal land description to GPS   |
| `reverse(longitude, latitude, *, survey_system=None, unit=None)`               | Find legal land description at GPS      |
| `autocomplete(query, *, limit=None, proximity=None)`                           | Get search suggestions                  |
| `batch_search(locations, *, chunk_size=100)`                                   | Batch convert up to 100+ descriptions   |
| `batch_reverse(coordinates, *, survey_system=None, unit=None, chunk_size=100)` | Batch reverse geocode up to 100+ points |
| `boundary(location)`                                                           | Get boundary polygon only               |
| `raw(location)`                                                                | Get raw GeoJSON FeatureCollection       |

All methods are also available on `AsyncTownshipCanada` as async/await.

### Return Types

**`SearchResult`** — returned by `search()`, `reverse()`

| Field            | Type                              | Description                  |
| ---------------- | --------------------------------- | ---------------------------- |
| `legal_location` | `str`                             | Normalized legal description |
| `latitude`       | `float`                           | Centroid latitude            |
| `longitude`      | `float`                           | Centroid longitude           |
| `province`       | `str`                             | Province name                |
| `survey_system`  | `str`                             | `DLS`, `NTS`, or `GTS`       |
| `unit`           | `str`                             | Resolution unit              |
| `boundary`       | `Polygon \| MultiPolygon \| None` | Grid boundary polygon        |
| `raw`            | `List[Feature]`                   | Raw GeoJSON features         |

**`BatchResult`** — returned by `batch_search()`, `batch_reverse()`

| Field     | Type                 | Description            |
| --------- | -------------------- | ---------------------- |
| `results`  | `List[SearchResult]`        | Successfully converted                    |
| `total`    | `int`                       | Total items submitted                     |
| `success`  | `int`                       | Successful conversions                    |
| `failed`   | `int`                       | Failed conversions                        |
| `failures` | `List[Tuple[str, str]]`     | `(location, error)` for each failed item  |

**`AutocompleteSuggestion`** — returned by `autocomplete()`

| Field            | Type    | Description                 |
| ---------------- | ------- | --------------------------- |
| `legal_location` | `str`   | Full legal land description |
| `latitude`       | `float` | Centroid latitude           |
| `longitude`      | `float` | Centroid longitude          |
| `survey_system`  | `str`   | Survey system               |
| `unit`           | `str`   | Resolution unit             |

### Exceptions

| Exception              | HTTP Status | Description                |
| ---------------------- | ----------- | -------------------------- |
| `ValidationError`      | 400         | Invalid request parameters |
| `AuthenticationError`  | 401         | Missing or invalid API key |
| `NotFoundError`        | 404         | No results found           |
| `RateLimitError`       | 429         | Rate limit exceeded        |
| `PayloadTooLargeError` | 413         | Batch exceeds 100 items    |
| `ServerError`          | 5xx         | Server-side error          |

```python
from townshipcanada import (
    TownshipCanada,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

tc = TownshipCanada("your_api_key")

try:
    result = tc.search("INVALID")
except NotFoundError:
    print("Location not found")
except AuthenticationError:
    print("Check your API key")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after}s")
```

## Supported Survey Systems

| System                                | Provinces  | Format Examples                                |
| ------------------------------------- | ---------- | ---------------------------------------------- |
| **DLS** (Dominion Land Survey)        | AB, SK, MB | `NW-36-42-3-W5`, `10-36-42-3-W5`, `36-42-3-W5` |
| **NTS** (National Topographic System) | BC         | `A-2-F/93-P-8`, `2-F/93-P-8`                   |
| **GTS** (Geographic Townships)        | ON         | `Lot 2 Con 4 Osprey`                           |

## Requirements

- Python 3.9+
- Dependencies: `httpx`, `pydantic`

## License

MIT — [Maps & Apps Inc.](https://townshipcanada.com)
