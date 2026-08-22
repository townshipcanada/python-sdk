"""Synchronous and asynchronous clients for the Township Canada API."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import httpx

try:
    _VERSION = _pkg_version("townshipcanada")
except Exception:
    _VERSION = "0.0.0-dev"

from .exceptions import (
    AuthenticationError,
    NotFoundError,
    PayloadTooLargeError,
    RateLimitError,
    ServerError,
    TownshipCanadaError,
    ValidationError,
)
from .models import (
    AgBatchResponse,
    AgReport,
    AutocompleteSuggestion,
    BatchMeta,
    BatchResult,
    EnergyBatchResponse,
    EnergyOperator,
    EnergyReport,
    Feature,
    FeatureCollection,
    MultiPolygon,
    Polygon,
    SearchResult,
)

BASE_URL = "https://developer.townshipcanada.com"
MAX_BATCH_SIZE = 100
MAX_REPORT_BATCH_SIZE = 25


def _raise_for_status(response: httpx.Response) -> None:
    """Translate HTTP error responses into typed exceptions."""
    if response.is_success:
        return

    code: Optional[str] = None
    try:
        body = response.json()
        error = body.get("error")
        if isinstance(error, dict):
            # Ag/Energy v1 error bodies: {"error": {"code", "message"}}
            message = error.get("message") or response.text
            code = error.get("code")
        else:
            message = body.get("message") or error or response.text
    except Exception:
        message = response.text

    status = response.status_code
    if status == 400:
        raise ValidationError(message, status_code=status, code=code)
    if status == 401:
        raise AuthenticationError(message, status_code=status, code=code)
    if status == 404:
        raise NotFoundError(message, status_code=status, code=code)
    if status == 413:
        raise PayloadTooLargeError(message, status_code=status, code=code)
    if status == 429:
        retry_after_raw = response.headers.get("retry-after")
        retry_after = float(retry_after_raw) if retry_after_raw else None
        raise RateLimitError(
            message, status_code=status, retry_after=retry_after, code=code
        )
    if status >= 500:
        raise ServerError(message, status_code=status, code=code)
    raise TownshipCanadaError(message, status_code=status, code=code)


def _parse_features(features: List[Feature]) -> SearchResult:
    """Extract a SearchResult from a list of centroid + grid features."""
    centroid = next((f for f in features if f.properties.shape == "centroid"), None)
    grid = next((f for f in features if f.properties.shape == "grid"), None)

    if not centroid or centroid.geometry.type != "Point":
        raise NotFoundError("No centroid found in response", status_code=404)

    coords = centroid.geometry.coordinates  # type: ignore[union-attr]
    boundary: Optional[Union[Polygon, MultiPolygon]] = None
    if grid and grid.geometry.type in ("Polygon", "MultiPolygon"):
        boundary = grid.geometry  # type: ignore[assignment]

    return SearchResult(
        legal_location=centroid.properties.legal_location or "",
        latitude=coords[1],
        longitude=coords[0],
        province=centroid.properties.province or "",
        survey_system=centroid.properties.survey_system or "",
        unit=centroid.properties.unit or "",
        boundary=boundary,
        raw=features,
    )


def _group_features_by_location(features: List[Feature]) -> Dict[str, List[Feature]]:
    """Group a flat list of features by their legal_location property."""
    groups: Dict[str, List[Feature]] = {}
    for feature in features:
        key = feature.properties.legal_location or ""
        groups.setdefault(key, []).append(feature)
    return groups


def _chunk(items: list, size: int) -> List[list]:
    """Split a list into chunks of the given size."""
    return [items[i : i + size] for i in range(0, len(items), size)]


def _parse_suggestions(fc: FeatureCollection) -> List[AutocompleteSuggestion]:
    """Convert an autocomplete FeatureCollection into suggestion objects."""
    return [
        AutocompleteSuggestion(
            legal_location=f.properties.legal_location or "",
            latitude=f.geometry.coordinates[1],  # type: ignore[union-attr]
            longitude=f.geometry.coordinates[0],  # type: ignore[union-attr]
            survey_system=f.properties.survey_system or "",
            unit=f.properties.unit or "",
        )
        for f in fc.features
    ]


def _autocomplete_params(
    query: str,
    limit: Optional[int],
    proximity: Optional[Tuple[float, float]],
) -> Dict[str, Union[str, int]]:
    """Build query params for the parcel autocomplete endpoint."""
    params: Dict[str, Union[str, int]] = {"location": query}
    if limit is not None:
        params["limit"] = limit
    if proximity is not None:
        params["proximity"] = f"{proximity[0]},{proximity[1]}"
    return params


def _report_autocomplete_params(
    query: str,
    limit: Optional[int],
    proximity: Optional[Tuple[float, float]],
) -> Dict[str, Union[str, int, float]]:
    """Build query params for the Ag/Energy v1 autocomplete endpoints.

    v1 takes ``q`` plus two explicit ``lat``/``lng`` params (the SDK keeps
    the ``proximity=(longitude, latitude)`` tuple for its own surface).
    """
    params: Dict[str, Union[str, int, float]] = {"q": query}
    if limit is not None:
        params["limit"] = limit
    if proximity is not None:
        params["lat"] = proximity[1]
        params["lng"] = proximity[0]
    return params


def _report_params(
    legal_location: str, include: Optional[Sequence[str]]
) -> Dict[str, str]:
    """Build query params shared by the report endpoints."""
    params: Dict[str, str] = {"legal_location": legal_location}
    if include:
        params["include"] = ",".join(include)
    return params


def _merge_batch_meta(target: BatchMeta, chunk: BatchMeta) -> None:
    """Sum one chunk's batch counters into the aggregate."""
    target.total += chunk.total
    target.ok += chunk.ok
    target.not_found += chunk.not_found
    target.error += chunk.error


# ---------------------------------------------------------------------------
# Synchronous client
# ---------------------------------------------------------------------------


class TownshipCanada:
    """Synchronous client for the Township Canada API.

    Args:
        api_key: Your Township Canada API key.
        base_url: Override the default API base URL.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise TownshipCanadaError("api_key is required")
        if not base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS to protect your API key in transit")
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": f"townshipcanada-python/{_VERSION}",
            },
            timeout=timeout,
        )

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "TownshipCanada":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # --- Search ---

    def search(self, location: str) -> SearchResult:
        """Convert a legal land description to GPS coordinates.

        Args:
            location: A legal land description, e.g.
                ``"NW-36-42-3-W5"`` (DLS), ``"A-2-F/93-P-8"`` (NTS),
                or ``"Lot 2 Con 4 Osprey"`` (GTS).

        Returns:
            A SearchResult with coordinates, boundary, and metadata.
        """
        response = self._client.get(
            "/search/legal-location", params={"location": location}
        )
        _raise_for_status(response)
        fc = FeatureCollection.model_validate(response.json())
        if not fc.features:
            raise NotFoundError(f'No results found for "{location}"')
        return _parse_features(fc.features)

    def reverse(
        self,
        longitude: float,
        latitude: float,
        *,
        survey_system: Optional[str] = None,
        unit: Optional[str] = None,
    ) -> SearchResult:
        """Find the legal land description at the given GPS coordinates.

        Args:
            longitude: Longitude (x) coordinate.
            latitude: Latitude (y) coordinate.
            survey_system: Filter by survey system (``"DLS"``, ``"NTS"``, ``"GTS"``).
            unit: Resolution unit (e.g. ``"Quarter Section"``, ``"LSD"``).

        Returns:
            A SearchResult with the matching legal land description.
        """
        params: Dict[str, str] = {"location": f"{longitude},{latitude}"}
        if survey_system is not None:
            params["survey_system"] = survey_system
        if unit is not None:
            params["unit"] = unit
        response = self._client.get("/search/coordinates", params=params)
        _raise_for_status(response)
        fc = FeatureCollection.model_validate(response.json())
        if not fc.features:
            raise NotFoundError(
                f"No results found for coordinates [{longitude}, {latitude}]"
            )
        return _parse_features(fc.features)

    # --- Autocomplete ---

    def autocomplete(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        proximity: Optional[Tuple[float, float]] = None,
    ) -> List[AutocompleteSuggestion]:
        """Get autocomplete suggestions for a partial legal land description.

        Args:
            query: Partial search query (minimum 2 characters).
            limit: Maximum number of suggestions (1-10, default 3).
            proximity: ``(longitude, latitude)`` tuple to bias results.

        Returns:
            A list of AutocompleteSuggestion objects.
        """
        params: Dict[str, Union[str, int]] = {"location": query}
        if limit is not None:
            params["limit"] = limit
        if proximity is not None:
            params["proximity"] = f"{proximity[0]},{proximity[1]}"
        response = self._client.get(
            "/autocomplete/legal-location", params=params
        )
        _raise_for_status(response)
        fc = FeatureCollection.model_validate(response.json())
        return [
            AutocompleteSuggestion(
                legal_location=f.properties.legal_location or "",
                latitude=f.geometry.coordinates[1],  # type: ignore[union-attr]
                longitude=f.geometry.coordinates[0],  # type: ignore[union-attr]
                survey_system=f.properties.survey_system or "",
                unit=f.properties.unit or "",
            )
            for f in fc.features
        ]

    # --- Batch ---

    def batch_search(
        self,
        locations: List[str],
        *,
        chunk_size: int = MAX_BATCH_SIZE,
    ) -> BatchResult:
        """Convert multiple legal land descriptions to GPS coordinates.

        Automatically chunks arrays larger than 100 (the API maximum per request).

        Args:
            locations: List of legal land descriptions.
            chunk_size: Max items per HTTP request (default/max 100).

        Returns:
            A BatchResult with results and success/failure counts.
        """
        chunk_size = min(chunk_size, MAX_BATCH_SIZE)
        all_results: List[SearchResult] = []
        total_failed = 0
        failures: List[Tuple[str, str]] = []

        for batch in _chunk(locations, chunk_size):
            response = self._client.post("/batch/legal-location", json=batch)
            _raise_for_status(response)
            fc = FeatureCollection.model_validate(response.json())
            grouped = _group_features_by_location(fc.features)
            for location_key, features in grouped.items():
                try:
                    all_results.append(_parse_features(features))
                except (NotFoundError, TownshipCanadaError) as exc:
                    total_failed += 1
                    failures.append((location_key, str(exc)))

        return BatchResult(
            results=all_results,
            total=len(locations),
            success=len(all_results),
            failed=total_failed,
            failures=failures,
        )

    def batch_reverse(
        self,
        coordinates: List[Tuple[float, float]],
        *,
        survey_system: Optional[str] = None,
        unit: Optional[str] = None,
        chunk_size: int = MAX_BATCH_SIZE,
    ) -> BatchResult:
        """Reverse geocode multiple coordinate pairs in one request.

        Automatically chunks arrays larger than 100 (the API maximum per request).

        Args:
            coordinates: List of ``(longitude, latitude)`` tuples.
            survey_system: Filter by survey system.
            unit: Resolution unit.
            chunk_size: Max items per HTTP request (default/max 100).

        Returns:
            A BatchResult with results and success/failure counts.
        """
        chunk_size = min(chunk_size, MAX_BATCH_SIZE)
        all_results: List[SearchResult] = []
        total_failed = 0
        failures: List[Tuple[str, str]] = []

        for batch in _chunk(list(coordinates), chunk_size):
            body: Dict[str, Any] = {"coordinates": [list(c) for c in batch]}
            if survey_system is not None:
                body["survey_system"] = survey_system
            if unit is not None:
                body["unit"] = unit
            response = self._client.post("/batch/coordinates", json=body)
            _raise_for_status(response)
            fc = FeatureCollection.model_validate(response.json())
            grouped = _group_features_by_location(fc.features)
            for location_key, features in grouped.items():
                try:
                    all_results.append(_parse_features(features))
                except (NotFoundError, TownshipCanadaError) as exc:
                    total_failed += 1
                    failures.append((location_key, str(exc)))

        return BatchResult(
            results=all_results,
            total=len(coordinates),
            success=len(all_results),
            failed=total_failed,
            failures=failures,
        )

    # --- Convenience ---

    def boundary(
        self, location: str
    ) -> Optional[Union[Polygon, MultiPolygon]]:
        """Get the boundary polygon for a legal land description.

        Args:
            location: A legal land description.

        Returns:
            The boundary as a GeoJSON Polygon or MultiPolygon, or None.
        """
        result = self.search(location)
        return result.boundary

    def raw(self, location: str) -> FeatureCollection:
        """Get the raw GeoJSON FeatureCollection for a legal land description.

        Args:
            location: A legal land description.

        Returns:
            The raw GeoJSON FeatureCollection from the API.
        """
        response = self._client.get(
            "/search/legal-location", params={"location": location}
        )
        _raise_for_status(response)
        return FeatureCollection.model_validate(response.json())

    # --- Ag API ---

    def ag_report(
        self,
        legal_location: str,
        *,
        include: Optional[Sequence[str]] = None,
    ) -> AgReport:
        """Get the agriculture parcel report for a quarter section or LSD.

        LSD inputs are resolved to their containing quarter section
        (``resolved_legal_location`` surfaces the resolved quarter).

        Args:
            legal_location: A quarter section (e.g. ``"NW-36-42-3-W5"``)
                or LSD (e.g. ``"10-36-42-3-W5"``).
            include: Section projection — return only these sections (the
                omitted sections are never queried). Valid values:
                ``productivity``, ``cropping``, ``soil``, ``land_use``,
                ``drought``, ``wetlands``, ``hydrology``, ``parcel_context``,
                ``provincial_detail``, ``geometry``. ``geometry`` attaches
                the boundary under ``parcel.geometry``.

        Returns:
            An AgReport. Sections degrade independently: an unavailable
            data layer is ``None`` rather than failing the report
            (``meta.unavailable`` says which and why).
        """
        response = self._client.get(
            "/ag/report", params=_report_params(legal_location, include)
        )
        _raise_for_status(response)
        return AgReport.model_validate(response.json())

    def ag_batch(self, locations: List[str]) -> AgBatchResponse:
        """Get agriculture reports for multiple locations in batch.

        Automatically chunks arrays larger than 25 (the API maximum per
        request). Results are returned in input order with per-item status;
        the ``meta`` counters are summed across chunks.

        Args:
            locations: List of quarter section or LSD legal locations.

        Returns:
            An AgBatchResponse (``results``, ``meta``). Each item carries
            ``legal_location``, ``status``, ``error`` (``{code, message}``
            or ``None``), and ``data``.
        """
        aggregate = AgBatchResponse()
        for batch in _chunk(locations, MAX_REPORT_BATCH_SIZE):
            response = self._client.post("/ag/batch", json=batch)
            _raise_for_status(response)
            chunk = AgBatchResponse.model_validate(response.json())
            aggregate.results.extend(chunk.results)
            _merge_batch_meta(aggregate.meta, chunk.meta)
        return aggregate

    def ag_autocomplete(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        proximity: Optional[Tuple[float, float]] = None,
    ) -> List[AutocompleteSuggestion]:
        """Suggest quarter sections with agriculture coverage as you type.

        Every suggestion is guaranteed to return a report.

        Args:
            query: Partial quarter section or LSD (e.g. ``"NW-36-42"``).
            limit: Maximum number of suggestions (1-10, default 3).
            proximity: ``(longitude, latitude)`` tuple to bias results
                (sent to the API as explicit ``lat``/``lng`` params).

        Returns:
            A list of AutocompleteSuggestion objects.
        """
        response = self._client.get(
            "/ag/autocomplete",
            params=_report_autocomplete_params(query, limit, proximity),
        )
        _raise_for_status(response)
        return _parse_suggestions(FeatureCollection.model_validate(response.json()))

    # --- Energy API ---

    def energy_report(
        self,
        legal_location: str,
        *,
        include: Optional[Sequence[str]] = None,
    ) -> EnergyReport:
        """Get the energy parcel report for a Legal Subdivision (LSD).

        Covers wells, pipelines, facilities, trailing-12-month production,
        Crown tenure, and alternative energy.

        Args:
            legal_location: An LSD legal location (e.g. ``"10-36-42-3-W5"``).
            include: Section projection — return only these sections (the
                omitted sections are never queried). Valid values:
                ``summary``, ``production``, ``tenure``, ``wells``,
                ``pipelines``, ``facilities``, ``alternative_energy``,
                ``geometry``. ``geometry`` attaches the LSD boundary under
                ``parcel.geometry``.

        Returns:
            An EnergyReport. A ``None`` section means no data at that
            location (or one source degraded — ``meta.unavailable`` says
            which); the rest of the report is still trustworthy. Array
            sections are ``{total, returned, truncated, more, rows}``
            envelopes.
        """
        response = self._client.get(
            "/energy/report", params=_report_params(legal_location, include)
        )
        _raise_for_status(response)
        return EnergyReport.model_validate(response.json())

    def energy_batch(self, locations: List[str]) -> EnergyBatchResponse:
        """Get energy reports for multiple LSDs in batch.

        Automatically chunks arrays larger than 25 (the API maximum per
        request). Results are returned in input order with per-item status;
        the ``meta`` counters are summed across chunks.

        Args:
            locations: List of LSD legal locations.

        Returns:
            An EnergyBatchResponse (``results``, ``meta``). Each item
            carries ``legal_location``, ``status``, ``error``
            (``{code, message}`` or ``None``), and ``data``.
        """
        aggregate = EnergyBatchResponse()
        for batch in _chunk(locations, MAX_REPORT_BATCH_SIZE):
            response = self._client.post("/energy/batch", json=batch)
            _raise_for_status(response)
            chunk = EnergyBatchResponse.model_validate(response.json())
            aggregate.results.extend(chunk.results)
            _merge_batch_meta(aggregate.meta, chunk.meta)
        return aggregate

    def energy_autocomplete(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        proximity: Optional[Tuple[float, float]] = None,
    ) -> List[AutocompleteSuggestion]:
        """Suggest LSDs with energy data, for typeahead inputs.

        Every suggestion is guaranteed to return a report.

        Args:
            query: Partial LSD (e.g. ``"10-36-42"``).
            limit: Maximum number of suggestions (1-10, default 3).
            proximity: ``(longitude, latitude)`` tuple to bias results
                (sent to the API as explicit ``lat``/``lng`` params).

        Returns:
            A list of AutocompleteSuggestion objects.
        """
        response = self._client.get(
            "/energy/autocomplete",
            params=_report_autocomplete_params(query, limit, proximity),
        )
        _raise_for_status(response)
        return _parse_suggestions(FeatureCollection.model_validate(response.json()))

    def energy_operator_autocomplete(
        self, query: str, *, limit: Optional[int] = None
    ) -> List[EnergyOperator]:
        """Search AER licensees by name or BA code for operator inputs.

        Prefix matches rank first, then by active well count descending.

        Args:
            query: Case-insensitive substring of the licensee name or
                BA code (minimum 2 characters).
            limit: Maximum number of matches (1-20, default 10).

        Returns:
            A list of EnergyOperator objects (each carries ``slug``, which
            routes straight to ``/energy/operators/{name}``).
        """
        params: Dict[str, Union[str, int]] = {"q": query}
        if limit is not None:
            params["limit"] = limit
        response = self._client.get("/energy/operators/autocomplete", params=params)
        _raise_for_status(response)
        return [
            EnergyOperator.model_validate(op)
            for op in response.json().get("rows", [])
        ]


# ---------------------------------------------------------------------------
# Asynchronous client
# ---------------------------------------------------------------------------


class AsyncTownshipCanada:
    """Asynchronous client for the Township Canada API.

    Args:
        api_key: Your Township Canada API key.
        base_url: Override the default API base URL.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise TownshipCanadaError("api_key is required")
        if not base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS to protect your API key in transit")
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
                "User-Agent": f"townshipcanada-python/{_VERSION}",
            },
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTownshipCanada":
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    # --- Search ---

    async def search(self, location: str) -> SearchResult:
        """Convert a legal land description to GPS coordinates.

        See :meth:`TownshipCanada.search` for full documentation.
        """
        response = await self._client.get(
            "/search/legal-location", params={"location": location}
        )
        _raise_for_status(response)
        fc = FeatureCollection.model_validate(response.json())
        if not fc.features:
            raise NotFoundError(f'No results found for "{location}"')
        return _parse_features(fc.features)

    async def reverse(
        self,
        longitude: float,
        latitude: float,
        *,
        survey_system: Optional[str] = None,
        unit: Optional[str] = None,
    ) -> SearchResult:
        """Find the legal land description at the given GPS coordinates.

        See :meth:`TownshipCanada.reverse` for full documentation.
        """
        params: Dict[str, str] = {"location": f"{longitude},{latitude}"}
        if survey_system is not None:
            params["survey_system"] = survey_system
        if unit is not None:
            params["unit"] = unit
        response = await self._client.get("/search/coordinates", params=params)
        _raise_for_status(response)
        fc = FeatureCollection.model_validate(response.json())
        if not fc.features:
            raise NotFoundError(
                f"No results found for coordinates [{longitude}, {latitude}]"
            )
        return _parse_features(fc.features)

    # --- Autocomplete ---

    async def autocomplete(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        proximity: Optional[Tuple[float, float]] = None,
    ) -> List[AutocompleteSuggestion]:
        """Get autocomplete suggestions for a partial legal land description.

        See :meth:`TownshipCanada.autocomplete` for full documentation.
        """
        params: Dict[str, Union[str, int]] = {"location": query}
        if limit is not None:
            params["limit"] = limit
        if proximity is not None:
            params["proximity"] = f"{proximity[0]},{proximity[1]}"
        response = await self._client.get(
            "/autocomplete/legal-location", params=params
        )
        _raise_for_status(response)
        fc = FeatureCollection.model_validate(response.json())
        return [
            AutocompleteSuggestion(
                legal_location=f.properties.legal_location or "",
                latitude=f.geometry.coordinates[1],  # type: ignore[union-attr]
                longitude=f.geometry.coordinates[0],  # type: ignore[union-attr]
                survey_system=f.properties.survey_system or "",
                unit=f.properties.unit or "",
            )
            for f in fc.features
        ]

    # --- Batch ---

    async def batch_search(
        self,
        locations: List[str],
        *,
        chunk_size: int = MAX_BATCH_SIZE,
    ) -> BatchResult:
        """Convert multiple legal land descriptions to GPS coordinates.

        See :meth:`TownshipCanada.batch_search` for full documentation.
        """
        chunk_size = min(chunk_size, MAX_BATCH_SIZE)
        all_results: List[SearchResult] = []
        total_failed = 0
        failures: List[Tuple[str, str]] = []

        for batch in _chunk(locations, chunk_size):
            response = await self._client.post("/batch/legal-location", json=batch)
            _raise_for_status(response)
            fc = FeatureCollection.model_validate(response.json())
            grouped = _group_features_by_location(fc.features)
            for location_key, features in grouped.items():
                try:
                    all_results.append(_parse_features(features))
                except (NotFoundError, TownshipCanadaError) as exc:
                    total_failed += 1
                    failures.append((location_key, str(exc)))

        return BatchResult(
            results=all_results,
            total=len(locations),
            success=len(all_results),
            failed=total_failed,
            failures=failures,
        )

    async def batch_reverse(
        self,
        coordinates: List[Tuple[float, float]],
        *,
        survey_system: Optional[str] = None,
        unit: Optional[str] = None,
        chunk_size: int = MAX_BATCH_SIZE,
    ) -> BatchResult:
        """Reverse geocode multiple coordinate pairs in one request.

        See :meth:`TownshipCanada.batch_reverse` for full documentation.
        """
        chunk_size = min(chunk_size, MAX_BATCH_SIZE)
        all_results: List[SearchResult] = []
        total_failed = 0
        failures: List[Tuple[str, str]] = []

        for batch in _chunk(list(coordinates), chunk_size):
            body: Dict[str, Any] = {"coordinates": [list(c) for c in batch]}
            if survey_system is not None:
                body["survey_system"] = survey_system
            if unit is not None:
                body["unit"] = unit
            response = await self._client.post("/batch/coordinates", json=body)
            _raise_for_status(response)
            fc = FeatureCollection.model_validate(response.json())
            grouped = _group_features_by_location(fc.features)
            for location_key, features in grouped.items():
                try:
                    all_results.append(_parse_features(features))
                except (NotFoundError, TownshipCanadaError) as exc:
                    total_failed += 1
                    failures.append((location_key, str(exc)))

        return BatchResult(
            results=all_results,
            total=len(coordinates),
            success=len(all_results),
            failed=total_failed,
            failures=failures,
        )

    # --- Convenience ---

    async def boundary(
        self, location: str
    ) -> Optional[Union[Polygon, MultiPolygon]]:
        """Get the boundary polygon for a legal land description.

        See :meth:`TownshipCanada.boundary` for full documentation.
        """
        result = await self.search(location)
        return result.boundary

    async def raw(self, location: str) -> FeatureCollection:
        """Get the raw GeoJSON FeatureCollection for a legal land description.

        See :meth:`TownshipCanada.raw` for full documentation.
        """
        response = await self._client.get(
            "/search/legal-location", params={"location": location}
        )
        _raise_for_status(response)
        return FeatureCollection.model_validate(response.json())

    # --- Ag API ---

    async def ag_report(
        self,
        legal_location: str,
        *,
        include: Optional[Sequence[str]] = None,
    ) -> AgReport:
        """Get the agriculture parcel report for a quarter section or LSD.

        See :meth:`TownshipCanada.ag_report` for full documentation.
        """
        response = await self._client.get(
            "/ag/report", params=_report_params(legal_location, include)
        )
        _raise_for_status(response)
        return AgReport.model_validate(response.json())

    async def ag_batch(self, locations: List[str]) -> AgBatchResponse:
        """Get agriculture reports for multiple locations in batch.

        See :meth:`TownshipCanada.ag_batch` for full documentation.
        """
        aggregate = AgBatchResponse()
        for batch in _chunk(locations, MAX_REPORT_BATCH_SIZE):
            response = await self._client.post("/ag/batch", json=batch)
            _raise_for_status(response)
            chunk = AgBatchResponse.model_validate(response.json())
            aggregate.results.extend(chunk.results)
            _merge_batch_meta(aggregate.meta, chunk.meta)
        return aggregate

    async def ag_autocomplete(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        proximity: Optional[Tuple[float, float]] = None,
    ) -> List[AutocompleteSuggestion]:
        """Suggest quarter sections with agriculture coverage as you type.

        See :meth:`TownshipCanada.ag_autocomplete` for full documentation.
        """
        response = await self._client.get(
            "/ag/autocomplete",
            params=_report_autocomplete_params(query, limit, proximity),
        )
        _raise_for_status(response)
        return _parse_suggestions(FeatureCollection.model_validate(response.json()))

    # --- Energy API ---

    async def energy_report(
        self,
        legal_location: str,
        *,
        include: Optional[Sequence[str]] = None,
    ) -> EnergyReport:
        """Get the energy parcel report for a Legal Subdivision (LSD).

        See :meth:`TownshipCanada.energy_report` for full documentation.
        """
        response = await self._client.get(
            "/energy/report", params=_report_params(legal_location, include)
        )
        _raise_for_status(response)
        return EnergyReport.model_validate(response.json())

    async def energy_batch(self, locations: List[str]) -> EnergyBatchResponse:
        """Get energy reports for multiple LSDs in batch.

        See :meth:`TownshipCanada.energy_batch` for full documentation.
        """
        aggregate = EnergyBatchResponse()
        for batch in _chunk(locations, MAX_REPORT_BATCH_SIZE):
            response = await self._client.post("/energy/batch", json=batch)
            _raise_for_status(response)
            chunk = EnergyBatchResponse.model_validate(response.json())
            aggregate.results.extend(chunk.results)
            _merge_batch_meta(aggregate.meta, chunk.meta)
        return aggregate

    async def energy_autocomplete(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        proximity: Optional[Tuple[float, float]] = None,
    ) -> List[AutocompleteSuggestion]:
        """Suggest LSDs with energy data, for typeahead inputs.

        See :meth:`TownshipCanada.energy_autocomplete` for full documentation.
        """
        response = await self._client.get(
            "/energy/autocomplete",
            params=_report_autocomplete_params(query, limit, proximity),
        )
        _raise_for_status(response)
        return _parse_suggestions(FeatureCollection.model_validate(response.json()))

    async def energy_operator_autocomplete(
        self, query: str, *, limit: Optional[int] = None
    ) -> List[EnergyOperator]:
        """Search AER licensees by name or BA code for operator inputs.

        See :meth:`TownshipCanada.energy_operator_autocomplete` for full
        documentation.
        """
        params: Dict[str, Union[str, int]] = {"q": query}
        if limit is not None:
            params["limit"] = limit
        response = await self._client.get(
            "/energy/operators/autocomplete", params=params
        )
        _raise_for_status(response)
        return [
            EnergyOperator.model_validate(op)
            for op in response.json().get("rows", [])
        ]
