"""Pydantic models for Township Canada API request and response types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# --- GeoJSON Models ---


class Point(BaseModel):
    """GeoJSON Point geometry."""

    type: Literal["Point"] = "Point"
    coordinates: List[float] = Field(
        ...,
        description="[longitude, latitude]",
        min_length=2,
        max_length=3,
    )

    @property
    def longitude(self) -> float:
        """Longitude (x) coordinate."""
        return self.coordinates[0]

    @property
    def latitude(self) -> float:
        """Latitude (y) coordinate."""
        return self.coordinates[1]


class Polygon(BaseModel):
    """GeoJSON Polygon geometry."""

    type: Literal["Polygon"] = "Polygon"
    coordinates: List[List[List[float]]] = Field(
        ..., description="Array of linear rings"
    )


class MultiPolygon(BaseModel):
    """GeoJSON MultiPolygon geometry."""

    type: Literal["MultiPolygon"] = "MultiPolygon"
    coordinates: List[List[List[List[float]]]] = Field(
        ..., description="Array of polygon coordinate arrays"
    )


class FeatureProperties(BaseModel):
    """Properties attached to each GeoJSON Feature returned by the API."""

    shape: Optional[Literal["grid", "centroid"]] = None
    legal_location: Optional[str] = None
    search_term: Optional[str] = None
    province: Optional[str] = Field(None, description="Canadian province")
    survey_system: Optional[str] = None
    unit: Optional[str] = None


class Feature(BaseModel):
    """GeoJSON Feature with Township Canada properties."""

    type: Literal["Feature"] = "Feature"
    geometry: Union[Point, Polygon, MultiPolygon] = Field(
        ..., discriminator="type"
    )
    properties: FeatureProperties = Field(default_factory=FeatureProperties)


class FeatureCollection(BaseModel):
    """GeoJSON FeatureCollection returned by Township Canada API endpoints."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[Feature] = Field(default_factory=list)

    @property
    def centroid(self) -> Optional[Feature]:
        """Return the centroid feature, if present."""
        for f in self.features:
            if f.properties.shape == "centroid":
                return f
        return None

    @property
    def grid(self) -> Optional[Feature]:
        """Return the grid (boundary) feature, if present."""
        for f in self.features:
            if f.properties.shape == "grid":
                return f
        return None


# --- Parsed Result Types ---


@dataclass
class SearchResult:
    """Parsed result from a search or reverse geocode call."""

    legal_location: str
    latitude: float
    longitude: float
    province: str
    survey_system: str
    unit: str
    boundary: Optional[Union[Polygon, MultiPolygon]]
    raw: List[Feature]


@dataclass
class BatchResult:
    """Aggregated result from a batch search or batch reverse call."""

    results: List[SearchResult] = field(default_factory=list)
    total: int = 0
    success: int = 0
    failed: int = 0
    failures: List[tuple] = field(default_factory=list)
    """List of ``(location, error_message)`` tuples for items that failed to parse."""


@dataclass
class AutocompleteSuggestion:
    """A single autocomplete suggestion."""

    legal_location: str
    latitude: float
    longitude: float
    survey_system: str
    unit: str


# --- Report Models (Ag & Energy APIs) ---


class _ReportSection(BaseModel):
    """Base for report sections: typed common fields, extra fields preserved."""

    model_config = ConfigDict(extra="allow")


class AgProductivity(_ReportSection):
    """LSRS/CLI land productivity ratings."""

    lsrs_score: Optional[float] = None
    lsrs_class: Optional[str] = None
    lsrs_limiter: Optional[str] = None
    cli_class: Optional[str] = None
    cli_score: Optional[float] = None
    cli_limiter: Optional[str] = None


class AgCropping(_ReportSection):
    """Crop rotation history."""

    dominant_crop: Optional[str] = None
    dominant_crop_name: Optional[str] = None
    dominant_category: Optional[str] = None
    rotation_pattern: Optional[str] = None
    diversity_index: Optional[float] = None
    years_covered: Optional[int] = None


class AgSoil(_ReportSection):
    """Soil classification."""

    order: Optional[str] = None
    group: Optional[str] = None
    subgroup: Optional[str] = None
    drainage_class: Optional[str] = None
    slope_class: Optional[str] = None
    parent_material: Optional[str] = None
    is_solonetzic: Optional[bool] = None
    source: Optional[str] = None


class AgLandUse(_ReportSection):
    """Land use classification and breakdown."""

    class_: Optional[str] = Field(None, alias="class")
    class_label: Optional[str] = None
    ipcc_class: Optional[str] = None
    breakdown: List[Dict[str, Any]] = Field(default_factory=list)


class AgDrought(_ReportSection):
    """Drought monitor classification."""

    drought_class: Optional[str] = None
    severity_label: Optional[str] = None
    valid_date: Optional[str] = None


class AgWetlands(_ReportSection):
    """Wetlands and hydrology."""

    source: Optional[str] = None
    count: Optional[int] = None
    area_ha: Optional[float] = None
    area_pct: Optional[float] = None
    dominant_type: Optional[str] = None
    on_parcel_water: Optional[bool] = None
    nearby_watercourse: Optional[bool] = None
    watercourse_name: Optional[str] = None
    watercourse_dist_m: Optional[float] = None


class AgParcelContext(_ReportSection):
    """Surrounding parcel context (municipality, railway, road, park)."""

    municipality: Optional[str] = None
    municipality_type: Optional[str] = None
    nearest_railway: Optional[Dict[str, Any]] = None
    nearest_road: Optional[Dict[str, Any]] = None
    nearest_park: Optional[Dict[str, Any]] = None


class AgReport(_ReportSection):
    """Agriculture parcel report, keyed at quarter-section grain.

    Sections degrade independently: an unavailable data layer is ``None``
    rather than failing the report.
    """

    legal_location: str
    qs_legal_location: Optional[str] = None
    """The containing quarter section, present when the input was an LSD."""
    province: Optional[str] = None
    area_ha: Optional[float] = None
    productivity: Optional[AgProductivity] = None
    cropping: Optional[AgCropping] = None
    soil: Optional[AgSoil] = None
    land_use: Optional[AgLandUse] = None
    drought: Optional[AgDrought] = None
    wetlands: Optional[AgWetlands] = None
    parcel_context: Optional[AgParcelContext] = None
    sk: Optional[Dict[str, Any]] = None
    """Saskatchewan extras (crown land, soils, pastures), only for SK parcels."""
    mb: Optional[Dict[str, Any]] = None
    """Manitoba extras (soil survey components), only for MB parcels."""
    geometry: Optional[Union[Polygon, MultiPolygon]] = None
    """Quarter-section boundary, only when requested with ``geometry=True``."""


class AgBatchItem(BaseModel):
    """Envelope for one item of an ag batch response (input order preserved)."""

    legal_location: str
    status: Literal["ok", "not_found", "error"]
    data: Optional[AgReport] = None
    error: Optional[str] = None


class EnergyActivity(_ReportSection):
    """Aggregated energy activity on the parcel."""

    total_wells: Optional[int] = None
    active_wells: Optional[int] = None
    suspended_wells: Optional[int] = None
    abandoned_wells: Optional[int] = None
    orphan_wells: Optional[int] = None
    recl_certified_wells: Optional[int] = None
    petrinex: Optional[Dict[str, Any]] = None
    pipeline_segments: Optional[int] = None
    pipeline_length_km: Optional[float] = None
    facility_count: Optional[int] = None
    facility_categories: List[str] = Field(default_factory=list)
    dominant_operator: Optional[str] = None


class EnergyProduction(_ReportSection):
    """Trailing-12-month Petrinex production."""

    oil_m3_12mo: Optional[float] = None
    gas_e3m3_12mo: Optional[float] = None
    water_m3_12mo: Optional[float] = None
    condensate_m3_12mo: Optional[float] = None
    has_oil: Optional[bool] = None
    has_gas: Optional[bool] = None
    has_water: Optional[bool] = None
    dominant_product: Optional[str] = None
    producing_wells: Optional[int] = None
    last_producing_month: Optional[str] = None


class EnergyTenure(_ReportSection):
    """A Crown tenure disposition intersecting the parcel."""

    tenure_kind: Optional[str] = None
    province: Optional[str] = None
    disposition_number: Optional[str] = None
    disposition_type: Optional[str] = None
    holder_name: Optional[str] = None
    status: Optional[str] = None
    expiry_date: Optional[str] = None
    days_to_expiry: Optional[int] = None
    is_expiring_soon: Optional[bool] = None
    is_perpetual: Optional[bool] = None
    area_ha: Optional[float] = None


class EnergyWell(_ReportSection):
    """A well on the parcel."""

    uwi: Optional[str] = None
    well_name: Optional[str] = None
    licence_number: Optional[str] = None
    licence_status: Optional[str] = None
    operator_name: Optional[str] = None
    fluid: Optional[str] = None
    mode: Optional[str] = None
    type: Optional[str] = None
    total_depth_m: Optional[float] = None
    is_orphan: Optional[bool] = None
    is_abandoned: Optional[bool] = None
    is_suspended: Optional[bool] = None


class EnergyPipeline(_ReportSection):
    """A pipeline segment crossing the parcel."""

    licence_line_number: Optional[str] = None
    licence_number: Optional[str] = None
    operator_name: Optional[str] = None
    segment_status: Optional[str] = None
    substance: Optional[str] = None
    length_m_on_parcel: Optional[float] = None
    total_length_km: Optional[float] = None


class EnergyReport(_ReportSection):
    """Per-parcel energy report, keyed at LSD grain.

    A ``None`` section or empty list means no data at that location (or one
    source degraded); the rest of the report is still trustworthy.
    """

    legal_location: str
    province: Optional[str] = None
    activity: Optional[EnergyActivity] = None
    production: Optional[EnergyProduction] = None
    tenure: List[EnergyTenure] = Field(default_factory=list)
    wells: List[EnergyWell] = Field(default_factory=list)
    pipelines: List[EnergyPipeline] = Field(default_factory=list)
    facilities: List[Dict[str, Any]] = Field(default_factory=list)
    alternative_energy: Optional[Dict[str, Any]] = None
    geometry: Optional[Union[Polygon, MultiPolygon]] = None
    """LSD boundary, only when requested with ``geometry=True``."""


class EnergyBatchItem(BaseModel):
    """Envelope for one item of an energy batch response (input order preserved)."""

    legal_location: str
    status: Literal["ok", "not_found", "error"]
    data: Optional[EnergyReport] = None
    error: Optional[str] = None


class EnergyOperator(BaseModel):
    """An AER licensee returned by operator autocomplete."""

    ba_code: Optional[str] = None
    name: str
    active_wells: Optional[int] = None
    abandoned_wells: Optional[int] = None
    orphan_wells: Optional[int] = None
