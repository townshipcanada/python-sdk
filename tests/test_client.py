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


AG_REPORT = {
    "legal_location": "NW-36-42-3-W5",
    "province": "ab",
    "area_ha": 64.75,
    "productivity": {
        "lsrs_score": 72,
        "lsrs_class": "2",
        "lsrs_limiter": "M - Moisture",
        "cli_class": "2",
        "cli_score": 80,
        "cli_limiter": "M",
    },
    "cropping": {
        "dominant_crop": "146",
        "dominant_crop_name": "Canola",
        "dominant_category": "Oilseed",
        "rotation_pattern": "Canola-Wheat",
        "diversity_index": 0.64,
        "years_covered": 10,
    },
    "soil": {
        "order": "Chernozemic",
        "group": "Black Chernozem",
        "subgroup": "Orthic Black Chernozem",
        "drainage_class": "Well drained",
        "slope_class": "2-5%",
        "parent_material": "Glacial till",
        "is_solonetzic": False,
        "source": "AGRASID",
    },
    "land_use": {
        "class": "51",
        "class_label": "Annual cropland",
        "ipcc_class": "Cropland",
        "breakdown": [{"class": "51", "label": "Annual cropland", "pct": 88.2}],
    },
    "drought": None,
    "wetlands": None,
    "parcel_context": {
        "municipality": "Red Deer County",
        "municipality_type": "Municipal District",
        "nearest_railway": None,
        "nearest_road": None,
        "nearest_park": None,
    },
}

ENERGY_REPORT = {
    "legal_location": "10-36-42-3-W5",
    "province": "ab",
    "activity": {
        "total_wells": 4,
        "active_wells": 2,
        "suspended_wells": 1,
        "abandoned_wells": 1,
        "orphan_wells": 0,
        "recl_certified_wells": 0,
        "petrinex": {"total": 4, "oil": 2, "gas": 2},
        "pipeline_segments": 3,
        "pipeline_length_km": 1.8,
        "facility_count": 1,
        "facility_categories": ["Battery"],
        "dominant_operator": "EXAMPLE ENERGY LTD",
    },
    "production": {
        "oil_m3_12mo": 1250.5,
        "gas_e3m3_12mo": 890.2,
        "water_m3_12mo": 3100.0,
        "condensate_m3_12mo": 0,
        "has_oil": True,
        "has_gas": True,
        "has_water": True,
        "dominant_product": "OIL",
        "producing_wells": 2,
        "last_producing_month": "2025-06",
    },
    "tenure": [
        {
            "tenure_kind": "png",
            "province": "ab",
            "disposition_number": "0512345",
            "holder_name": "EXAMPLE ENERGY LTD",
            "status": "active",
            "expiry_date": "2027-03-01",
            "days_to_expiry": 192,
            "is_expiring_soon": True,
            "is_perpetual": False,
            "area_ha": 256,
        }
    ],
    "wells": [
        {
            "uwi": "100103604203W500",
            "well_name": "EXAMPLE 10-36",
            "operator_name": "EXAMPLE ENERGY LTD",
            "fluid": "Crude Oil",
            "is_orphan": False,
        }
    ],
    "pipelines": [],
    "facilities": [],
    "alternative_energy": None,
}

OPERATORS_RESPONSE = {
    "operators": [
        {
            "ba_code": "0AB1",
            "name": "EXAMPLE ENERGY LTD",
            "active_wells": 1250,
            "abandoned_wells": 320,
            "orphan_wells": 0,
        }
    ]
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

    # --- Ag API ---

    @respx.mock
    def test_ag_report(self):
        route = respx.get(f"{BASE}/ag/report").mock(
            return_value=Response(200, json=AG_REPORT)
        )

        with TownshipCanada("test-key") as tc:
            report = tc.ag_report("NW-36-42-3-W5")

        assert "legal_location=NW-36-42-3-W5" in str(route.calls[0].request.url)
        assert "geometry" not in str(route.calls[0].request.url)
        assert report.legal_location == "NW-36-42-3-W5"
        assert report.province == "ab"
        assert report.area_ha == pytest.approx(64.75)
        assert report.productivity is not None
        assert report.productivity.lsrs_score == 72
        assert report.soil is not None
        assert report.soil.order == "Chernozemic"
        assert report.land_use is not None
        assert report.land_use.class_ == "51"
        assert report.drought is None
        assert report.wetlands is None

    @respx.mock
    def test_ag_report_with_geometry(self):
        report_with_geometry = {
            **AG_REPORT,
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-114.65, 52.12], [-114.65, 52.13], [-114.64, 52.13], [-114.65, 52.12]]
                ],
            },
        }
        route = respx.get(f"{BASE}/ag/report").mock(
            return_value=Response(200, json=report_with_geometry)
        )

        with TownshipCanada("test-key") as tc:
            report = tc.ag_report("NW-36-42-3-W5", geometry=True)

        assert "geometry=true" in str(route.calls[0].request.url)
        assert report.geometry is not None
        assert report.geometry.type == "Polygon"

    @respx.mock
    def test_ag_report_bc_not_supported(self):
        respx.get(f"{BASE}/ag/report").mock(
            return_value=Response(
                400, json={"message": "BC locations are not yet supported"}
            )
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(ValidationError, match="BC locations"):
                tc.ag_report("A-2-F/93-P-8")

    @respx.mock
    def test_ag_report_not_found(self):
        respx.get(f"{BASE}/ag/report").mock(
            return_value=Response(404, json={"message": "No agriculture data"})
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(NotFoundError):
                tc.ag_report("NW-1-1-1-W4")

    @respx.mock
    def test_ag_batch(self):
        batch_response = [
            {"legal_location": "NW-36-42-3-W5", "status": "ok", "data": AG_REPORT},
            {
                "legal_location": "not a location",
                "status": "error",
                "error": "Invalid legal location format",
                "data": None,
            },
            {"legal_location": "NW-1-1-1-W4", "status": "not_found", "data": None},
        ]
        route = respx.post(f"{BASE}/ag/batch").mock(
            return_value=Response(200, json=batch_response)
        )

        with TownshipCanada("test-key") as tc:
            items = tc.ag_batch(["NW-36-42-3-W5", "not a location", "NW-1-1-1-W4"])

        import json

        body = json.loads(route.calls[0].request.content)
        assert body == ["NW-36-42-3-W5", "not a location", "NW-1-1-1-W4"]

        assert len(items) == 3
        assert items[0].status == "ok"
        assert items[0].data is not None
        assert items[0].data.area_ha == pytest.approx(64.75)
        assert items[1].status == "error"
        assert items[1].error == "Invalid legal location format"
        assert items[2].status == "not_found"
        assert items[2].data is None

    @respx.mock
    def test_ag_batch_auto_chunks(self):
        respx.post(f"{BASE}/ag/batch").mock(return_value=Response(200, json=[]))

        locations = [f"NW-{i}-42-3-W5" for i in range(60)]

        with TownshipCanada("test-key") as tc:
            tc.ag_batch(locations)

        # 60 items with chunk size 25 -> 3 requests (25 + 25 + 10)
        assert len(respx.calls) == 3

    @respx.mock
    def test_ag_autocomplete(self):
        route = respx.get(f"{BASE}/ag/autocomplete").mock(
            return_value=Response(200, json=AUTOCOMPLETE_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            suggestions = tc.ag_autocomplete("NW-36", limit=5, proximity=(-114.0, 51.0))

        url = str(route.calls[0].request.url)
        assert "location=NW-36" in url
        assert "limit=5" in url
        assert "proximity=-114.0%2C51.0" in url
        assert len(suggestions) == 2
        assert suggestions[0].legal_location == "NW-36-42-3-W5"

    # --- Energy API ---

    @respx.mock
    def test_energy_report(self):
        route = respx.get(f"{BASE}/energy/report").mock(
            return_value=Response(200, json=ENERGY_REPORT)
        )

        with TownshipCanada("test-key") as tc:
            report = tc.energy_report("10-36-42-3-W5")

        assert "legal_location=10-36-42-3-W5" in str(route.calls[0].request.url)
        assert report.legal_location == "10-36-42-3-W5"
        assert report.activity is not None
        assert report.activity.total_wells == 4
        assert report.activity.dominant_operator == "EXAMPLE ENERGY LTD"
        assert report.production is not None
        assert report.production.dominant_product == "OIL"
        assert len(report.tenure) == 1
        assert report.tenure[0].holder_name == "EXAMPLE ENERGY LTD"
        assert len(report.wells) == 1
        assert report.wells[0].uwi == "100103604203W500"
        assert report.pipelines == []
        assert report.alternative_energy is None

    @respx.mock
    def test_energy_report_with_geometry(self):
        route = respx.get(f"{BASE}/energy/report").mock(
            return_value=Response(200, json=ENERGY_REPORT)
        )

        with TownshipCanada("test-key") as tc:
            tc.energy_report("10-36-42-3-W5", geometry=True)

        assert "geometry=true" in str(route.calls[0].request.url)

    @respx.mock
    def test_energy_report_not_found(self):
        respx.get(f"{BASE}/energy/report").mock(
            return_value=Response(404, json={"message": "No energy data"})
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(NotFoundError):
                tc.energy_report("1-1-1-1-W4")

    @respx.mock
    def test_energy_batch(self):
        batch_response = [
            {"legal_location": "10-36-42-3-W5", "status": "ok", "data": ENERGY_REPORT},
            {"legal_location": "1-1-1-1-W4", "status": "not_found", "data": None},
        ]
        respx.post(f"{BASE}/energy/batch").mock(
            return_value=Response(200, json=batch_response)
        )

        with TownshipCanada("test-key") as tc:
            items = tc.energy_batch(["10-36-42-3-W5", "1-1-1-1-W4"])

        assert len(items) == 2
        assert items[0].status == "ok"
        assert items[0].data is not None
        assert items[0].data.activity.total_wells == 4
        assert items[1].status == "not_found"

    @respx.mock
    def test_energy_batch_auto_chunks(self):
        respx.post(f"{BASE}/energy/batch").mock(return_value=Response(200, json=[]))

        locations = [f"10-{i}-42-3-W5" for i in range(30)]

        with TownshipCanada("test-key") as tc:
            tc.energy_batch(locations)

        # 30 items with chunk size 25 -> 2 requests (25 + 5)
        assert len(respx.calls) == 2

    @respx.mock
    def test_energy_autocomplete(self):
        route = respx.get(f"{BASE}/energy/autocomplete").mock(
            return_value=Response(200, json=AUTOCOMPLETE_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            suggestions = tc.energy_autocomplete("10-36-42")

        assert "location=10-36-42" in str(route.calls[0].request.url)
        assert len(suggestions) == 2

    @respx.mock
    def test_energy_operator_autocomplete(self):
        route = respx.get(f"{BASE}/energy/operators/autocomplete").mock(
            return_value=Response(200, json=OPERATORS_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            operators = tc.energy_operator_autocomplete("example", limit=20)

        url = str(route.calls[0].request.url)
        assert "q=example" in url
        assert "limit=20" in url
        assert len(operators) == 1
        assert operators[0].ba_code == "0AB1"
        assert operators[0].name == "EXAMPLE ENERGY LTD"
        assert operators[0].active_wells == 1250

    @respx.mock
    def test_energy_operator_autocomplete_empty(self):
        respx.get(f"{BASE}/energy/operators/autocomplete").mock(
            return_value=Response(200, json={"operators": []})
        )

        with TownshipCanada("test-key") as tc:
            operators = tc.energy_operator_autocomplete("zzzz")

        assert operators == []

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
    async def test_ag_report(self):
        respx.get(f"{BASE}/ag/report").mock(
            return_value=Response(200, json=AG_REPORT)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            report = await tc.ag_report("NW-36-42-3-W5")

        assert report.legal_location == "NW-36-42-3-W5"
        assert report.productivity is not None
        assert report.productivity.lsrs_score == 72

    @respx.mock
    @pytest.mark.asyncio
    async def test_ag_batch(self):
        respx.post(f"{BASE}/ag/batch").mock(
            return_value=Response(
                200,
                json=[
                    {"legal_location": "NW-36-42-3-W5", "status": "ok", "data": AG_REPORT}
                ],
            )
        )

        async with AsyncTownshipCanada("test-key") as tc:
            items = await tc.ag_batch(["NW-36-42-3-W5"])

        assert len(items) == 1
        assert items[0].status == "ok"

    @respx.mock
    @pytest.mark.asyncio
    async def test_ag_autocomplete(self):
        respx.get(f"{BASE}/ag/autocomplete").mock(
            return_value=Response(200, json=AUTOCOMPLETE_RESPONSE)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            suggestions = await tc.ag_autocomplete("NW-36")

        assert len(suggestions) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_energy_report(self):
        respx.get(f"{BASE}/energy/report").mock(
            return_value=Response(200, json=ENERGY_REPORT)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            report = await tc.energy_report("10-36-42-3-W5")

        assert report.legal_location == "10-36-42-3-W5"
        assert report.activity is not None
        assert report.activity.total_wells == 4

    @respx.mock
    @pytest.mark.asyncio
    async def test_energy_batch(self):
        respx.post(f"{BASE}/energy/batch").mock(
            return_value=Response(
                200,
                json=[
                    {"legal_location": "1-1-1-1-W4", "status": "not_found", "data": None}
                ],
            )
        )

        async with AsyncTownshipCanada("test-key") as tc:
            items = await tc.energy_batch(["1-1-1-1-W4"])

        assert len(items) == 1
        assert items[0].status == "not_found"

    @respx.mock
    @pytest.mark.asyncio
    async def test_energy_autocomplete(self):
        respx.get(f"{BASE}/energy/autocomplete").mock(
            return_value=Response(200, json=AUTOCOMPLETE_RESPONSE)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            suggestions = await tc.energy_autocomplete("10-36-42")

        assert len(suggestions) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_energy_operator_autocomplete(self):
        respx.get(f"{BASE}/energy/operators/autocomplete").mock(
            return_value=Response(200, json=OPERATORS_RESPONSE)
        )

        async with AsyncTownshipCanada("test-key") as tc:
            operators = await tc.energy_operator_autocomplete("example")

        assert len(operators) == 1
        assert operators[0].ba_code == "0AB1"

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_handling(self):
        respx.get(f"{BASE}/search/legal-location").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )

        async with AsyncTownshipCanada("bad-key") as tc:
            with pytest.raises(AuthenticationError):
                await tc.search("NW-36-42-3-W5")
