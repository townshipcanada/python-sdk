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
    "legal_location": "10-36-42-3-W5",
    "resolved_legal_location": "NE-36-42-3-W5",
    "grain": "lsd",
    "province": "AB",
    "parcel": {
        "area_ha": 64.75,
        "centroid": {"lat": 52.61, "lng": -113.82},
        "geometry": None,
    },
    "productivity": {
        "lsrs": {"score": 72, "class": "2", "limiter": "M - Moisture"},
        "cli": {"score": 80, "class": "2", "limiter": "M"},
    },
    "cropping": {
        "dominant": {"code": "146", "name": "Canola", "category": "Oilseed"},
        "rotation": "Canola-Wheat",
        "diversity_index": 0.6412,
        "years_covered": 10,
    },
    "soil": {
        "classification": {
            "order": "Chernozemic",
            "great_group": "Black Chernozem",
            "subgroup_code": "Orthic Black Chernozem",
        },
        "drainage_class": "Well drained",
        "slope_class": "2-5%",
        "parent_material": "Glacial till",
        "is_solonetzic": False,
        "source": "AGRASID",
    },
    "land_use": {
        "dominant": {"code": "51", "label": "Annual cropland", "ipcc_class": "Cropland"},
        "breakdown": [
            {"code": "51", "label": "Annual cropland", "ipcc_class": "Cropland", "pct": 88.2}
        ],
    },
    "drought": {"class": "D1", "severity_label": "Moderate Drought", "as_of": "2026-07"},
    "wetlands": None,
    "hydrology": {
        "watercourse": {"name": "Blindman River", "distance_m": 240, "is_on_parcel": False},
        "water_body": {
            "name": None,
            "distance_m": None,
            "is_on_parcel": False,
            "on_parcel_pct": None,
        },
        "search_radius_m": 500,
    },
    "parcel_context": {
        "municipality": {"name": "Red Deer County", "type": "Municipal District"},
        "nearest_railway": None,
        "nearest_road": None,
        "nearest_park": None,
    },
    "provincial_detail": None,
    "units": {"area": "ha", "distance": "m"},
    "meta": {
        "unavailable": [],
        "sources": {"soil": {"name": "AGRASID / SLC v3.2", "as_of": None}},
    },
}

ENERGY_REPORT = {
    "legal_location": "10-36-42-3-W5",
    "province": "AB",
    "parcel": {
        "area_ha": 16.19,
        "centroid": {"lat": 52.51, "lng": -113.71},
        "geometry": None,
    },
    "summary": {
        "wells": {
            "total": 4,
            "active": 2,
            "suspended": 1,
            "abandoned": 1,
            "orphan": 0,
            "reclamation_certified": 0,
            "primary_source": "regulator",
            "by_source": {
                "regulator": {
                    "total": 4,
                    "active": 2,
                    "suspended": 1,
                    "abandoned": 1,
                    "orphan": 0,
                    "reclamation_certified": 0,
                },
                "petrinex": {
                    "total": 4,
                    "active": 2,
                    "suspended": 1,
                    "abandoned": 1,
                    "oil": 2,
                    "gas": 2,
                    "water": 0,
                },
            },
        },
        "pipelines": {"segment_count": 3, "length_m_on_parcel": 1800},
        "facilities": {"count": 1, "categories": ["Battery"]},
        "operators": {
            "dominant": {
                "name": "EXAMPLE ENERGY LTD",
                "ba_code": None,
                "slug": "example-energy-ltd",
                "well_count": 4,
                "well_share_pct": 100,
                "share_basis": "regulator_total_wells",
            }
        },
        "last_activity_date": "2024-11-03",
    },
    "production": {
        "window_months": 12,
        "last_producing_month": "2025-06",
        "volumes": {
            "oil_m3": 1250.5,
            "gas_e3m3": 890.2,
            "condensate_m3": 0,
            "water_m3": 3100.0,
        },
        "has_oil": True,
        "has_gas": True,
        "has_condensate": False,
        "has_water": True,
        "dominant_product": "oil",
        "producing_well_count": 2,
    },
    "tenure": {
        "total": 1,
        "returned": 1,
        "truncated": False,
        "more": "/energy/tenure?legal_location=10-36-42-3-W5",
        "rows": [
            {
                "id": "0512345",
                "href": "/energy/dispositions/0512345",
                "tenure_kind": "png",
                "province": "AB",
                "disposition_number": "0512345",
                "mineral_category": None,
                "disposition_type": "licence",
                "disposition_type_raw": "NAT GAS LIC",
                "target_substance": None,
                "coal_category": None,
                "holder": {
                    "name": "EXAMPLE ENERGY LTD",
                    "ba_code": None,
                    "slug": "example-energy-ltd",
                },
                "status": "active",
                "expiry_date": "2027-03-01",
                "days_to_expiry": 192,
                "expiry_state": "expiring_soon",
                "area_ha": 256,
                "lsd_coverage_pct": 100,
                "is_transfer_pending": False,
                "overlap_point": {"lat": 52.5, "lng": -113.7},
            }
        ],
    },
    "wells": {
        "total": 1,
        "returned": 1,
        "truncated": False,
        "more": "/energy/wells?legal_location=10-36-42-3-W5",
        "rows": [
            {
                "id": "100103604203W500",
                "uwi": "100103604203W500",
                "well_name": "EXAMPLE 10-36",
                "licence_number": "0400001",
                "status": "active",
                "licence_status_raw": "Issued",
                "operator": {"name": None, "ba_code": "0AB1", "slug": None},
                "fluid": "crude_oil",
                "mode": "pumping",
                "type": "development",
                "total_depth_m": 1650,
                "is_orphan": False,
                "is_abandoned": False,
                "is_suspended": False,
                "location": {"lat": 52.51, "lng": -113.71},
            }
        ],
    },
    "pipelines": {"total": 0, "returned": 0, "truncated": False, "more": None, "rows": []},
    "facilities": {"total": 0, "returned": 0, "truncated": False, "more": None, "rows": []},
    "alternative_energy": None,
    "units": {
        "length": "m",
        "area": "ha",
        "depth": "m",
        "pressure": "kPa",
        "oil": "m3",
        "gas": "e3m3",
    },
    "meta": {"unavailable": [], "sources": {"production": {"name": "Petrinex", "as_of": None}}},
}

OPERATORS_RESPONSE = {
    "rows": [
        {
            "name": "EXAMPLE ENERGY LTD",
            "ba_code": "0AB1",
            "slug": "example-energy-ltd",
            "active_wells": 1250,
            "abandoned_wells": 320,
            "orphan_wells": 0,
        }
    ],
    "meta": {"q": "example", "limit": 10},
}

EMPTY_BATCH_RESPONSE = {
    "results": [],
    "meta": {"total": 0, "ok": 0, "not_found": 0, "error": 0},
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
            report = tc.ag_report("10-36-42-3-W5")

        assert "legal_location=10-36-42-3-W5" in str(route.calls[0].request.url)
        assert "include" not in str(route.calls[0].request.url)
        assert report.legal_location == "10-36-42-3-W5"
        assert report.resolved_legal_location == "NE-36-42-3-W5"
        assert report.grain == "lsd"
        assert report.province == "AB"
        assert report.parcel is not None
        assert report.parcel.area_ha == pytest.approx(64.75)
        assert report.parcel.centroid is not None
        assert report.parcel.centroid.lat == pytest.approx(52.61)
        assert report.productivity is not None
        assert report.productivity.lsrs is not None
        assert report.productivity.lsrs.score == 72
        assert report.productivity.lsrs.class_ == "2"
        assert report.soil is not None
        assert report.soil.classification is not None
        assert report.soil.classification.order == "Chernozemic"
        assert report.soil.classification.great_group == "Black Chernozem"
        assert report.cropping is not None
        assert report.cropping.dominant is not None
        assert report.cropping.dominant.name == "Canola"
        assert report.cropping.rotation == "Canola-Wheat"
        assert report.land_use is not None
        assert report.land_use.dominant is not None
        assert report.land_use.dominant.code == "51"
        assert report.land_use.breakdown[0].pct == pytest.approx(88.2)
        assert report.drought is not None
        assert report.drought.class_ == "D1"
        assert report.drought.as_of == "2026-07"
        assert report.hydrology is not None
        assert report.hydrology.watercourse is not None
        assert report.hydrology.watercourse.distance_m == 240
        assert report.wetlands is None
        assert report.provincial_detail is None
        assert report.parcel_context is not None
        assert report.parcel_context.municipality is not None
        assert report.parcel_context.municipality.name == "Red Deer County"
        assert report.meta is not None
        assert report.meta.unavailable == []

    @respx.mock
    def test_ag_report_with_include(self):
        report_with_geometry = {
            **AG_REPORT,
            "parcel": {
                **AG_REPORT["parcel"],
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-114.65, 52.12], [-114.65, 52.13], [-114.64, 52.13], [-114.65, 52.12]]
                    ],
                },
            },
        }
        route = respx.get(f"{BASE}/ag/report").mock(
            return_value=Response(200, json=report_with_geometry)
        )

        with TownshipCanada("test-key") as tc:
            report = tc.ag_report(
                "NW-36-42-3-W5", include=["soil", "drought", "geometry"]
            )

        assert "include=soil%2Cdrought%2Cgeometry" in str(route.calls[0].request.url)
        assert report.parcel is not None
        assert report.parcel.geometry is not None
        assert report.parcel.geometry.type == "Polygon"

    @respx.mock
    def test_ag_report_bc_not_supported(self):
        respx.get(f"{BASE}/ag/report").mock(
            return_value=Response(
                400,
                json={
                    "error": {
                        "code": "bc_not_supported",
                        "message": "BC locations are not yet supported",
                    }
                },
            )
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(ValidationError, match="BC locations") as exc_info:
                tc.ag_report("A-2-F/93-P-8")

        assert exc_info.value.code == "bc_not_supported"

    @respx.mock
    def test_ag_report_not_found(self):
        respx.get(f"{BASE}/ag/report").mock(
            return_value=Response(
                404,
                json={"error": {"code": "not_found", "message": "No agriculture data"}},
            )
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(NotFoundError) as exc_info:
                tc.ag_report("NW-1-1-1-W4")

        assert exc_info.value.code == "not_found"

    @respx.mock
    def test_ag_batch(self):
        batch_response = {
            "results": [
                {
                    "legal_location": "NW-36-42-3-W5",
                    "status": "ok",
                    "error": None,
                    "data": AG_REPORT,
                },
                {
                    "legal_location": "not a location",
                    "status": "error",
                    "error": {
                        "code": "invalid_legal_location",
                        "message": "Not a quarter section or LSD.",
                    },
                    "data": None,
                },
                {
                    "legal_location": "NW-1-1-1-W4",
                    "status": "not_found",
                    "error": None,
                    "data": None,
                },
            ],
            "meta": {"total": 3, "ok": 1, "not_found": 1, "error": 1},
        }
        route = respx.post(f"{BASE}/ag/batch").mock(
            return_value=Response(200, json=batch_response)
        )

        with TownshipCanada("test-key") as tc:
            batch = tc.ag_batch(["NW-36-42-3-W5", "not a location", "NW-1-1-1-W4"])

        import json

        body = json.loads(route.calls[0].request.content)
        assert body == ["NW-36-42-3-W5", "not a location", "NW-1-1-1-W4"]

        assert len(batch.results) == 3
        assert batch.results[0].status == "ok"
        assert batch.results[0].error is None
        assert batch.results[0].data is not None
        assert batch.results[0].data.parcel is not None
        assert batch.results[0].data.parcel.area_ha == pytest.approx(64.75)
        assert batch.results[1].status == "error"
        assert batch.results[1].error is not None
        assert batch.results[1].error.code == "invalid_legal_location"
        assert batch.results[2].status == "not_found"
        assert batch.results[2].data is None
        assert batch.meta.total == 3
        assert batch.meta.ok == 1
        assert batch.meta.not_found == 1
        assert batch.meta.error == 1

    @respx.mock
    def test_ag_batch_auto_chunks(self):
        respx.post(f"{BASE}/ag/batch").mock(
            return_value=Response(
                200,
                json={
                    "results": [],
                    "meta": {"total": 25, "ok": 20, "not_found": 4, "error": 1},
                },
            )
        )

        locations = [f"NW-{i}-42-3-W5" for i in range(60)]

        with TownshipCanada("test-key") as tc:
            batch = tc.ag_batch(locations)

        # 60 items with chunk size 25 -> 3 requests (25 + 25 + 10)
        assert len(respx.calls) == 3
        # meta counters are summed across chunks
        assert batch.meta.total == 75
        assert batch.meta.ok == 60

    @respx.mock
    def test_ag_autocomplete(self):
        route = respx.get(f"{BASE}/ag/autocomplete").mock(
            return_value=Response(200, json=AUTOCOMPLETE_RESPONSE)
        )

        with TownshipCanada("test-key") as tc:
            suggestions = tc.ag_autocomplete("NW-36", limit=5, proximity=(-114.0, 51.0))

        url = str(route.calls[0].request.url)
        assert "q=NW-36" in url
        assert "limit=5" in url
        assert "lat=51.0" in url
        assert "lng=-114.0" in url
        assert "proximity" not in url
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
        assert "include" not in str(route.calls[0].request.url)
        assert report.legal_location == "10-36-42-3-W5"
        assert report.province == "AB"
        assert report.parcel is not None
        assert report.parcel.area_ha == pytest.approx(16.19)
        assert report.summary is not None
        assert report.summary.wells is not None
        assert report.summary.wells.total == 4
        assert report.summary.wells.primary_source == "regulator"
        assert report.summary.wells.by_source is not None
        assert report.summary.wells.by_source["petrinex"].oil == 2
        assert report.summary.operators is not None
        assert report.summary.operators.dominant is not None
        assert report.summary.operators.dominant.name == "EXAMPLE ENERGY LTD"
        assert report.summary.operators.dominant.slug == "example-energy-ltd"
        assert report.production is not None
        assert report.production.dominant_product == "oil"
        assert report.production.volumes is not None
        assert report.production.volumes.oil_m3 == pytest.approx(1250.5)
        assert report.production.producing_well_count == 2
        assert report.tenure is not None
        assert report.tenure.total == 1
        assert report.tenure.truncated is False
        row = report.tenure.rows[0]
        assert row.id == "0512345"
        assert row.href == "/energy/dispositions/0512345"
        assert row.holder is not None
        assert row.holder.name == "EXAMPLE ENERGY LTD"
        assert row.days_to_expiry == 192
        assert row.expiry_state == "expiring_soon"
        assert report.wells is not None
        assert report.wells.rows[0].uwi == "100103604203W500"
        assert report.wells.rows[0].operator is not None
        assert report.wells.rows[0].operator.ba_code == "0AB1"
        assert report.wells.rows[0].location is not None
        assert report.wells.rows[0].location.lat == pytest.approx(52.51)
        assert report.pipelines is not None
        assert report.pipelines.rows == []
        assert report.alternative_energy is None
        assert report.units is not None
        assert report.units["gas"] == "e3m3"

    @respx.mock
    def test_energy_report_with_include(self):
        route = respx.get(f"{BASE}/energy/report").mock(
            return_value=Response(200, json=ENERGY_REPORT)
        )

        with TownshipCanada("test-key") as tc:
            tc.energy_report("10-36-42-3-W5", include=["summary", "geometry"])

        assert "include=summary%2Cgeometry" in str(route.calls[0].request.url)

    @respx.mock
    def test_energy_report_not_found(self):
        respx.get(f"{BASE}/energy/report").mock(
            return_value=Response(
                404, json={"error": {"code": "not_found", "message": "No energy data"}}
            )
        )

        with TownshipCanada("test-key") as tc:
            with pytest.raises(NotFoundError) as exc_info:
                tc.energy_report("1-1-1-1-W4")

        assert exc_info.value.code == "not_found"

    @respx.mock
    def test_energy_batch(self):
        batch_response = {
            "results": [
                {
                    "legal_location": "10-36-42-3-W5",
                    "status": "ok",
                    "error": None,
                    "data": ENERGY_REPORT,
                },
                {
                    "legal_location": "1-1-1-1-W4",
                    "status": "not_found",
                    "error": None,
                    "data": None,
                },
            ],
            "meta": {"total": 2, "ok": 1, "not_found": 1, "error": 0},
        }
        respx.post(f"{BASE}/energy/batch").mock(
            return_value=Response(200, json=batch_response)
        )

        with TownshipCanada("test-key") as tc:
            batch = tc.energy_batch(["10-36-42-3-W5", "1-1-1-1-W4"])

        assert len(batch.results) == 2
        assert batch.results[0].status == "ok"
        assert batch.results[0].error is None
        assert batch.results[0].data is not None
        assert batch.results[0].data.summary is not None
        assert batch.results[0].data.summary.wells.total == 4
        assert batch.results[1].status == "not_found"
        assert batch.meta.total == 2
        assert batch.meta.ok == 1

    @respx.mock
    def test_energy_batch_auto_chunks(self):
        respx.post(f"{BASE}/energy/batch").mock(
            return_value=Response(200, json=EMPTY_BATCH_RESPONSE)
        )

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

        assert "q=10-36-42" in str(route.calls[0].request.url)
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
        assert operators[0].slug == "example-energy-ltd"
        assert operators[0].active_wells == 1250

    @respx.mock
    def test_energy_operator_autocomplete_empty(self):
        respx.get(f"{BASE}/energy/operators/autocomplete").mock(
            return_value=Response(200, json={"rows": [], "meta": {"q": "zzzz", "limit": 10}})
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
            report = await tc.ag_report("10-36-42-3-W5")

        assert report.legal_location == "10-36-42-3-W5"
        assert report.resolved_legal_location == "NE-36-42-3-W5"
        assert report.productivity is not None
        assert report.productivity.lsrs is not None
        assert report.productivity.lsrs.score == 72

    @respx.mock
    @pytest.mark.asyncio
    async def test_ag_batch(self):
        respx.post(f"{BASE}/ag/batch").mock(
            return_value=Response(
                200,
                json={
                    "results": [
                        {
                            "legal_location": "NW-36-42-3-W5",
                            "status": "ok",
                            "error": None,
                            "data": AG_REPORT,
                        }
                    ],
                    "meta": {"total": 1, "ok": 1, "not_found": 0, "error": 0},
                },
            )
        )

        async with AsyncTownshipCanada("test-key") as tc:
            batch = await tc.ag_batch(["NW-36-42-3-W5"])

        assert len(batch.results) == 1
        assert batch.results[0].status == "ok"
        assert batch.meta.ok == 1

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
        assert report.summary is not None
        assert report.summary.wells is not None
        assert report.summary.wells.total == 4

    @respx.mock
    @pytest.mark.asyncio
    async def test_energy_batch(self):
        respx.post(f"{BASE}/energy/batch").mock(
            return_value=Response(
                200,
                json={
                    "results": [
                        {
                            "legal_location": "1-1-1-1-W4",
                            "status": "not_found",
                            "error": None,
                            "data": None,
                        }
                    ],
                    "meta": {"total": 1, "ok": 0, "not_found": 1, "error": 0},
                },
            )
        )

        async with AsyncTownshipCanada("test-key") as tc:
            batch = await tc.energy_batch(["1-1-1-1-W4"])

        assert len(batch.results) == 1
        assert batch.results[0].status == "not_found"
        assert batch.meta.not_found == 1

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
