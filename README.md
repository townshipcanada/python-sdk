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

### 4. Agriculture: Pull a Parcel Report

```python
from townshipcanada import TownshipCanada

tc = TownshipCanada("your_api_key")

# Quarter section or LSD input (LSDs resolve to their containing quarter)
report = tc.ag_report("NW-36-42-3-W5")

print(report.parcel.area_ha)                # 64.75
print(report.productivity.lsrs.score)       # 72
print(report.soil.classification.order)     # "Chernozemic"
print(report.cropping.rotation)             # "Canola-Wheat"
print(report.drought.class_)                # "D1"

# Only the sections you need (the rest are never queried);
# "geometry" attaches the boundary under parcel.geometry
slim = tc.ag_report("NW-36-42-3-W5", include=["soil", "drought", "geometry"])

# Multiple locations: loop over ag_report
for location in ["NW-36-42-3-W5", "10-2-24-28-W4"]:
    print(location, tc.ag_report(location, include=["soil"]).soil.classification.order)
```

### 5. Energy: Wells, Pipelines, and Tenure on an LSD

```python
from townshipcanada import TownshipCanada

tc = TownshipCanada("your_api_key")

report = tc.energy_report("10-36-42-3-W5")

print(report.summary.wells.total)                   # 4
print(report.summary.operators.dominant.name)       # "EXAMPLE ENERGY LTD"
if report.production:
    print(report.production.volumes.oil_m3)         # 1250.5
# Array sections are envelopes: total is the true count, `more` links to
# the unbounded collection endpoint when the report caps the rows
print(report.wells.total, report.wells.truncated)
for well in report.wells.rows:
    print(well.uwi, well.operator.name, well.status)
for row in report.tenure.rows:
    print(row.id, row.expiry_state, row.days_to_expiry)  # signed; negative = expired
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

**Ag API** — agriculture parcel reports (quarter-section grain; AB, SK, MB):

| Method                                                    | Description                                          |
| --------------------------------------------------------- | ---------------------------------------------------- |
| `ag_report(legal_location, *, include=None)`               | Agriculture report for a quarter section or LSD; `include` projects sections (`productivity`, `cropping`, `soil`, `land_use`, `drought`, `wetlands`, `hydrology`, `parcel_context`, `provincial_detail`, `geometry`) |

The Ag API also serves the eight per-section routes (`/ag/productivity`, `/ag/cropping`, `/ag/soil`, `/ag/land-use`, `/ag/drought`, `/ag/wetlands`, `/ag/hydrology`, `/ag/parcel-context`), which return the same section payloads `ag_report` embeds — use `include=[...]` to fetch just what you need in one call. For legal-location typeahead, use `autocomplete()`.

**Energy API** — per-parcel energy reports (LSD grain; AB, SK, MB):

| Method                                                        | Description                                       |
| ------------------------------------------------------------- | ------------------------------------------------- |
| `energy_report(legal_location, *, include=None)`               | Energy report for an LSD; `include` projects sections (`summary`, `production`, `tenure`, `wells`, `pipelines`, `facilities`, `alternative_energy`, `geometry`) |

The Energy API also serves the per-section routes (`/energy/summary`, `/energy/production`, `/energy/alternative-energy`), the unbounded collection routes the report's `more` links point at (`/energy/wells`, `/energy/pipelines`, `/energy/facilities`, `/energy/tenure`), and the cross-parcel routes (`/energy/operators`, `/energy/operators/{name}`, `/energy/tenure/expiring`, `/energy/dispositions/{number}`, `/energy/pipelines/{licence}`). Operator typeahead is served by `GET /energy/operators?q=`.

BC (NTS) locations are not yet supported by the Ag and Energy APIs and raise `ValidationError` with `code="bc_not_supported"`.

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

**`AgReport`** — returned by `ag_report()`

| Field                                                                             | Type                              | Description                                      |
| --------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------ |
| `legal_location`                                                                   | `str`                             | Input legal location (canonicalized)             |
| `resolved_legal_location`                                                          | `Optional[str]`                   | The quarter section the report describes (always sent) |
| `grain`                                                                            | `Optional[str]`                   | `"quarter_section"` or `"lsd"`                   |
| `province`                                                                         | `Optional[str]`                   | Uppercase: `AB`, `SK`, or `MB`                   |
| `parcel`                                                                           | `Optional[AgParcel]`              | `area_ha`, `centroid`, `geometry` (with `include=["geometry"]`) |
| `productivity`, `cropping`, `soil`, `land_use`, `drought`, `wetlands`, `hydrology`, `parcel_context` | section models or `None` | Sections degrade independently to `None`; omitted when projected out |
| `provincial_detail`                                                                | `Optional[AgProvincialDetail]`    | SK crown land / soils / pastures, MB soils; `None` for AB |
| `units` / `meta`                                                                   | `dict` / `ReportMeta`             | Units block and `{unavailable, sources}` metadata |

**`EnergyReport`** — returned by `energy_report()`

| Field                              | Type                              | Description                             |
| ---------------------------------- | --------------------------------- | --------------------------------------- |
| `legal_location`                   | `str`                             | Input LSD                               |
| `province`                         | `Optional[str]`                   | Uppercase: `AB`, `SK`, or `MB`          |
| `parcel`                           | `Optional[EnergyParcel]`          | `area_ha`, `centroid`, `geometry` (with `include=["geometry"]`) |
| `summary`                          | `Optional[EnergySummary]`         | Well/pipeline/facility rollups, dominant operator |
| `production`                       | `Optional[EnergyProduction]`      | Trailing-12-month Petrinex production (`volumes.oil_m3`, ...) |
| `tenure` / `wells` / `pipelines` / `facilities` | section envelopes    | `{total, returned, truncated, more, rows}`; typed rows |
| `alternative_energy`               | `Optional[dict]`                  | CCS/geothermal envelopes, when present  |
| `units` / `meta`                   | `dict` / `ReportMeta`             | Units block and `{unavailable, sources}` metadata |

Tenure rows carry a **signed** `days_to_expiry` (negative = expired) and `expiry_state` (`expired`, `expires_today`, `expiring_soon`, `active`, `perpetual`). Companies are `OperatorRef` objects (`name`, `ba_code`, `slug`) under `operator` / `holder` / `licensee`. Points are `LatLng` objects under `location`, `overlap_point`, or `centroid`.

Report models keep unrecognized fields (Pydantic `extra="allow"`), so new API fields are preserved on the parsed objects.

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

For the Ag and Energy APIs, exceptions also expose the machine-readable code from the v1 error body (`{"error": {"code", "message"}}`) as `e.code` — e.g. `invalid_parameter`, `invalid_legal_location`, `bc_not_supported`, `not_found`, `rate_limit_exceeded`.

## Migrating to v2 (Ag & Energy v1 contract)

v2.0.0 tracks the breaking v1 reshape of the Ag and Energy APIs. The parcel `search`/`reverse`/`batch_*`/`autocomplete` surface is unchanged.

**Removed surfaces**

Ag and Energy batch and autocomplete are not available in 2.0.0. `ag_batch`, `energy_batch`, `ag_autocomplete`, `energy_autocomplete`, and `energy_operator_autocomplete` (sync and async) have no counterpart — the underlying endpoints were retired, along with the `AgBatchResponse`/`AgBatchItem`/`EnergyBatchResponse`/`EnergyBatchItem`/`BatchMeta`/`BatchItemError`/`EnergyOperator` models. Loop over `ag_report`/`energy_report` for multiple locations, use `autocomplete()` for legal-location typeahead, and `GET /energy/operators?q=` for operator typeahead.

**Request changes**

- `ag_report`/`energy_report`: `geometry=True` is gone — pass `include=["geometry"]`. `include` also projects reports down to just the sections you need.

**Response changes**

- `AgReport`: `qs_legal_location` → `resolved_legal_location` (always present) plus new `grain`; root `area_ha` → `parcel.area_ha` (plus `parcel.centroid`/`parcel.geometry`); `productivity` is nested (`productivity.lsrs.score`, not `lsrs_score`); `cropping.dominant_crop*` → `cropping.dominant` (`code`/`name`/`category`) and `rotation_pattern` → `rotation`; `soil.group`/`soil.subgroup` → `soil.classification` (`order`/`great_group`/`subgroup_code`); `land_use` is `dominant` + `breakdown` with string codes; `drought` is `class_`/`severity_label`/`as_of` (`"YYYY-MM"`); new `hydrology` section; `sk`/`mb` → `provincial_detail`; new `units` and `meta`.
- `EnergyReport`: `activity` → `summary` (well/pipeline/facility rollups with `by_source` and `operators.dominant`); `production` is `window_months` + `volumes` (`oil_m3`, not `oil_m3_12mo`) with lowercase enums; array sections are `{total, returned, truncated, more, rows}` envelopes; tenure rows carry signed `days_to_expiry` and `expiry_state` (replacing `is_expiring_soon`/`is_perpetual`); companies are `OperatorRef` objects (`operator`/`holder`/`licensee`); pipeline rows rename `mop_kpa` → `max_operating_pressure_kpa` and `total_length_km` → `segment_length_km`; points are `LatLng` objects; new `parcel`, `units`, `meta`. Provinces are uppercase (`"AB"`).
- Errors: v1 error bodies are `{"error": {"code", "message"}}`; SDK exceptions now expose `.code`.

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
