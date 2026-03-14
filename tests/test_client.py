"""Tests for the Township Canada Python SDK."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from townshipcanada import (
    AsyncTownshipCanada,
    AuthenticationError,
    NotFoundError,
    PayloadTooLargeError,
    RateLimitError,
    TownshipCanada,
    TownshipCanadaError,
    ValidationError,
)
from townshipcanada.exceptions import ServerError

BASE = "https://developer.townshipcanada.com"

# --- Fixtures ---

SEARCH_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-114.65, 52.12],
                        [-114.65, 52.13],
                        [-114.64, 52.13],
                        [-114.64, 52.12],
                        [-114.65, 52.12],
                    ]
                ],
            },
            "properties": {
                "shape": "grid",
                "legal_location": "NW-36-42-3-W5",
                "search_term": "NW-36-42-3-W5",
                "province": "Alberta",
                "survey_system": "DLS",
                "unit": "Quarter Section",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-114.648933, 52.454928]},
            "properties": {
                "shape": "centroid",
                "legal_location": "NW-36-42-3-W5",
                "search_term": "NW-36-42-3-W5",
                "province": "Alberta",
                "survey_system": "DLS",
                "unit": "Quarter Section",
            },
        },
    ],
}

AUTOCOMPLETE_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-114.648933, 52.454928]},
            "properties": {
                "legal_location": "NW-36-42-3-W5",
                "search_term": "NW-36",
                "survey_system": "DLS",
                "unit": "Quarter Section",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-114.123, 51.456]},
            "properties": {
                "legal_location": "NW-36-42-3-W4",
                "search_term": "NW-36",
                "survey_system": "DLS",
                "unit": "Quarter Section",
            },
        },
    ],
}

BATCH_RESPONSE = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-114.65, 52.12],
                        [-114.65, 52.13],
                        [-114.64, 52.13],
                        [-114.64, 52.12],
                        [-114.65, 52.12],
                    ]
                ],
            },
            "properties": {
                "shape": "grid",
                "legal_location": "NW-36-42-3-W5",
                "search_term": "NW-36-42-3-W5",
                "province": "Alberta",
                "survey_system": "DLS",
                "unit": "Quarter Section",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-114.648933, 52.454928]},
            "properties": {
                "shape": "centroid",
                "legal_location": "NW-36-42-3-W5",
                "search_term": "NW-36-42-3-W5",
                "province": "Alberta",
                "survey_system": "DLS",
                "unit": "Quarter Section",
            },
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-114.07, 51.04],
                        [-114.07, 51.05],
                        [-114.06, 51.05],
                        [-114.06, 51.04],
                        [-114.07, 51.04],
                    ]
                ],
            },
            "properties": {
                "shape": "grid",
                "legal_location": "SE-1-50-10-W4",
                "search_term": "SE-1-50-10-W4",
                "province": "Alberta",
                "survey_system": "DLS",
                "unit": "Quarter Section",
            },
        },
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-114.072, 51.045]},
            "properties": {
                "shape": "centroid",
                "legal_location": "SE-1-50-10-W4",
                "search_term": "SE-1-50-10-W4",
                "province": "Alberta",
                "survey_system": "DLS",
                "unit": "Quarter Section",
            },
        },
    ],
}


# --- Sync Client Tests ---


class TestTownshipCanada:
    def test_constructor_requires_api_key(self):
        with pytest.raises(TownshipCanadaError, match="api_key is required"):
            TownshipCanada("")

    def test_constructor_requires_https(self):
        with pytest.raises(ValueError, match="HTTPS"):
            TownshipCanada("key", base_url="http://example.com")

    @respx.mock
    def test_search(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            result = tc.search("NW-36-42-3-W5")

        assert result.legal_location == "NW-36-42-3-W5"
        assert result.latitude == pytest.approx(52.454928)
        assert result.longitude == pytest.approx(-114.648933)
        assert result.province == "Alberta"
        assert result.survey_system == "DLS"
        assert result.unit == "Quarter Section"
        assert result.boundary is not None
        assert result.boundary.type == "Polygon"

    @respx.mock
    def test_search_not_found(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(200, json={"type": "FeatureCollection", "features": []})
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(NotFoundError):
                tc.search("INVALID")

    @respx.mock
    def test_reverse(self):
        respx.get(f"{BASE}/search/coordinates").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            result = tc.reverse(-114.648933, 52.454928)

        assert result.legal_location == "NW-36-42-3-W5"
        assert result.province == "Alberta"

    @respx.mock
    def test_reverse_with_options(self):
        route = respx.get(f"{BASE}/search/coordinates").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            tc.reverse(-114.648933, 52.454928, survey_system="DLS", unit="Quarter Section")

        assert "survey_system=DLS" in str(route.calls[0].request.url)
        assert "unit=Quarter+Section" in str(route.calls[0].request.url)

    @respx.mock
    def test_autocomplete(self):
        respx.get(f"{BASE}/autocomplete/legal-location").mock(
            return_value=Response(200, json=AUTOCOMPLETE_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            suggestions = tc.autocomplete("NW-36")

        assert len(suggestions) == 2
        assert suggestions[0].legal_location == "NW-36-42-3-W5"
        assert suggestions[0].latitude == pytest.approx(52.454928)
        assert suggestions[1].legal_location == "NW-36-42-3-W4"

    @respx.mock
    def test_autocomplete_with_options(self):
        route = respx.get(f"{BASE}/autocomplete/legal-location").mock(
            return_value=Response(200, json=AUTOCOMPLETE_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            tc.autocomplete("NW-36", limit=5, proximity=(-114.0, 51.0))

        url = str(route.calls[0].request.url)
        assert "limit=5" in url
        assert "proximity=-114.0%2C51.0" in url

    @respx.mock
    def test_batch_search(self):
        respx.post(f"{BASE}/batch/legal-location").mock(
            return_value=Response(200, json=BATCH_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            result = tc.batch_search(["NW-36-42-3-W5", "SE-1-50-10-W4"])

        assert result.total == 2
        assert result.success == 2
        assert result.failed == 0
        assert len(result.results) == 2
        assert result.results[0].legal_location == "NW-36-42-3-W5"
        assert result.results[1].legal_location == "SE-1-50-10-W4"

    @respx.mock
    def test_batch_search_auto_chunks(self):
        respx.post(f"{BASE}/batch/legal-location").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        locations = [f"NW-{i}-42-3-W5" for i in range(150)]

        with TownshipCanada("test-key") as tc:
            tc.batch_search(locations)

        # 150 items with chunk_size=100 -> 2 requests
        assert len(respx.calls) == 2

    @respx.mock
    def test_batch_reverse(self):
        respx.post(f"{BASE}/batch/coordinates").mock(
            return_value=Response(200, json=BATCH_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            result = tc.batch_reverse([(-114.648933, 52.454928), (-114.072, 51.045)])

        assert result.total == 2
        assert result.success == 2

    @respx.mock
    def test_boundary(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            boundary = tc.boundary("NW-36-42-3-W5")

        assert boundary is not None
        assert boundary.type == "Polygon"

    @respx.mock
    def test_raw(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            fc = tc.raw("NW-36-42-3-W5")

        assert fc.type == "FeatureCollection"
        assert len(fc.features) == 2
        assert fc.centroid is not None
        assert fc.grid is not None

    # --- Error handling ---

    @respx.mock
    def test_error_401(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        with TownshipCanada("bad-key") as tc:
            with pytest.raises(AuthenticationError):
                tc.search("NW-36-42-3-W5")

    @respx.mock
    def test_error_400(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(400, json={"message": "Bad Request"})
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(ValidationError):
                tc.search("bad")

    @respx.mock
    def test_error_404(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(404, json={"error": "Not Found"})
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(NotFoundError):
                tc.search("NW-99-99-99-W9")

    @respx.mock
    def test_error_413(self):
        respx.post(f"{BASE}/batch/legal-location").mock(
            return_value=Response(413, json={"error": "Payload Too Large"})
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(PayloadTooLargeError):
                tc.batch_search(["a"] * 50)

    @respx.mock
    def test_error_429(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(
                429,
                json={"error": "Rate Limit Exceeded"},
                headers={"Retry-After": "60"},
            )
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(RateLimitError) as exc_info:
                tc.search("NW-36-42-3-W5")

        assert exc_info.value.retry_after == 60.0

    @respx.mock
    def test_error_500(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(500, json={"error": "Internal Server Error"})
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(ServerError):
                tc.search("NW-36-42-3-W5")

    # --- API key header ---

    @respx.mock
    def test_sends_api_key_header(self):
        route = respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        with TownshipCanada("my-secret-key") as tc:
            tc.search("NW-36-42-3-W5")

        assert route.calls[0].request.headers["x-api-key"] == "my-secret-key"

    @respx.mock
    def test_sends_user_agent(self):
        route = respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            tc.search("NW-36-42-3-W5")

        assert "townshipcanada-python" in route.calls[0].request.headers["user-agent"]


# --- Async Client Tests ---


class TestAsyncTownshipCanada:
    @respx.mock
    @pytest.mark.asyncio
    async def test_search(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            result = await tc.search("NW-36-42-3-W5")

        assert result.legal_location == "NW-36-42-3-W5"
        assert result.latitude == pytest.approx(52.454928)

    @respx.mock
    @pytest.mark.asyncio
    async def test_reverse(self):
        respx.get(f"{BASE}/search/coordinates").mock(
            return_value=Response(200, json=SEARCH_RESPONSE)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            result = await tc.reverse(-114.648933, 52.454928)

        assert result.legal_location == "NW-36-42-3-W5"

    @respx.mock
    @pytest.mark.asyncio
    async def test_autocomplete(self):
        respx.get(f"{BASE}/autocomplete/legal-location").mock(
            return_value=Response(200, json=AUTOCOMPLETE_RESPONSE)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            suggestions = await tc.autocomplete("NW-36")

        assert len(suggestions) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_batch_search(self):
        respx.post(f"{BASE}/batch/legal-location").mock(
            return_value=Response(200, json=BATCH_RESPONSE)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            result = await tc.batch_search(["NW-36-42-3-W5", "SE-1-50-10-W4"])

        assert result.total == 2
        assert result.success == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_batch_reverse(self):
        respx.post(f"{BASE}/batch/coordinates").mock(
            return_value=Response(200, json=BATCH_RESPONSE)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            result = await tc.batch_reverse([(-114.648933, 52.454928), (-114.072, 51.045)])

        assert result.total == 2
        assert result.success == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_handling(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        async with AsyncTownshipCanada("bad-key") as tc:
            with pytest.raises(AuthenticationError):
                await tc.search("NW-36-42-3-W5")
