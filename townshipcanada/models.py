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

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class LatLng(_ReportSection):
    """A point as ``{lat, lng}`` (report payloads use this, not GeoJSON)."""

    lat: Optional[float] = None
    lng: Optional[float] = None


class OperatorRef(_ReportSection):
    """A company reference: ``{name, ba_code, slug}``.

    ``slug`` is the ``/energy/operators/{name}`` routing slug. ``ba_code``
    is ``None`` where the source value is not a real BA code.
    """

    name: Optional[str] = None
    ba_code: Optional[str] = None
    slug: Optional[str] = None


class UnavailableSection(_ReportSection):
    """A section that could not be served, listed under ``meta.unavailable``."""

    section: Optional[str] = None
    reason: Optional[str] = None
    """``source_error``, ``not_published_in_province``, or ``timeout``."""


class SectionSource(_ReportSection):
    """Upstream source of one report section (``as_of`` is None for now)."""

    name: Optional[str] = None
    as_of: Optional[str] = None


class ReportMeta(_ReportSection):
    """The ``meta`` block every report and section response carries."""

    unavailable: List[UnavailableSection] = Field(default_factory=list)
    sources: Dict[str, SectionSource] = Field(default_factory=dict)


# --- Ag API models ---


class AgParcel(_ReportSection):
    """Parcel block: ``area_ha`` is guaranteed; full reports add centroid/geometry."""

    area_ha: Optional[float] = None
    centroid: Optional[LatLng] = None
    geometry: Optional[Union[Polygon, MultiPolygon]] = None
    """GeoJSON when requested with ``include=["geometry", ...]``, else None."""


class AgProductivityRating(_ReportSection):
    """One productivity rating (LSRS or CLI): score, class, limiter."""

    score: Optional[float] = None
    class_: Optional[str] = Field(None, alias="class")
    limiter: Optional[str] = None


class AgProductivity(_ReportSection):
    """LSRS/CLI land productivity ratings."""

    lsrs: Optional[AgProductivityRating] = None
    cli: Optional[AgProductivityRating] = None


class AgDominantCrop(_ReportSection):
    """The dominant crop: code, name, category."""

    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None


class AgCropping(_ReportSection):
    """Crop rotation history."""

    dominant: Optional[AgDominantCrop] = None
    rotation: Optional[str] = None
    diversity_index: Optional[float] = None
    years_covered: Optional[int] = None


class AgSoilClassification(_ReportSection):
    """Canadian System of Soil Classification levels."""

    order: Optional[str] = None
    great_group: Optional[str] = None
    subgroup_code: Optional[str] = None


class AgSoil(_ReportSection):
    """Soil classification."""

    classification: Optional[AgSoilClassification] = None
    drainage_class: Optional[str] = None
    slope_class: Optional[str] = None
    parent_material: Optional[str] = None
    is_solonetzic: Optional[bool] = None
    source: Optional[str] = None


class AgLandUseClass(_ReportSection):
    """One land-use class: string code, label, IPCC class."""

    code: Optional[str] = None
    label: Optional[str] = None
    ipcc_class: Optional[str] = None


class AgLandUseBreakdown(AgLandUseClass):
    """One land-use breakdown row (class plus its share of the parcel)."""

    pct: Optional[float] = None


class AgLandUse(_ReportSection):
    """Land use classification and breakdown."""

    dominant: Optional[AgLandUseClass] = None
    breakdown: List[AgLandUseBreakdown] = Field(default_factory=list)


class AgDrought(_ReportSection):
    """Drought monitor classification."""

    class_: Optional[str] = Field(None, alias="class")
    """Drought monitor class, e.g. ``"D1"``."""
    severity_label: Optional[str] = None
    as_of: Optional[str] = None
    """Month fact, ``"YYYY-MM"``."""


class AgWetlands(_ReportSection):
    """ABMI wetland coverage (Alberta only)."""

    source: Optional[str] = None
    count: Optional[int] = None
    area_ha: Optional[float] = None
    area_pct: Optional[float] = None
    water_pct: Optional[float] = None
    dominant_type: Optional[str] = None
    on_parcel_water: Optional[bool] = None
    classes: Optional[Dict[str, float]] = None
    hydro_period: Optional[str] = None


class AgHydrologyFeature(_ReportSection):
    """Nearest watercourse or water body within the search radius."""

    name: Optional[str] = None
    distance_m: Optional[float] = None
    is_on_parcel: Optional[bool] = None
    on_parcel_pct: Optional[float] = None
    """Share of the parcel an intersecting water body covers (water bodies only)."""


class AgHydrology(_ReportSection):
    """Nearest watercourse / water body (national layer, all provinces)."""

    watercourse: Optional[AgHydrologyFeature] = None
    water_body: Optional[AgHydrologyFeature] = None
    search_radius_m: Optional[float] = None


class AgMunicipality(_ReportSection):
    """The municipality containing the parcel."""

    name: Optional[str] = None
    type: Optional[str] = None


class AgNearestFeature(_ReportSection):
    """A nearby railway, road, or park with its distance."""

    name: Optional[str] = None
    distance_m: Optional[float] = None


class AgParcelContext(_ReportSection):
    """Surrounding parcel context (municipality, railway, road, park)."""

    municipality: Optional[AgMunicipality] = None
    nearest_railway: Optional[AgNearestFeature] = None
    nearest_road: Optional[AgNearestFeature] = None
    nearest_park: Optional[AgNearestFeature] = None


class AgProvincialDetail(_ReportSection):
    """Province-specific extras.

    Saskatchewan supplies ``crown_land``, ``soils``, and ``pastures``;
    Manitoba supplies ``soils`` only. ``None`` for Alberta parcels.
    """

    crown_land: Optional[List[Dict[str, Any]]] = None
    soils: Optional[List[Dict[str, Any]]] = None
    pastures: Optional[List[Dict[str, Any]]] = None


class AgReport(_ReportSection):
    """Agriculture parcel report, keyed at quarter-section grain.

    Sections degrade independently: an unavailable data layer is ``None``
    rather than failing the report (``meta.unavailable`` says which and
    why). Sections are ``None`` when omitted by an ``include=`` projection.
    """

    legal_location: str
    resolved_legal_location: Optional[str] = None
    """The quarter section the report describes — always sent by the API."""
    grain: Optional[str] = None
    """``"quarter_section"`` or ``"lsd"`` — the grain of your input."""
    province: Optional[str] = None
    """Uppercase province code: ``"AB" | "SK" | "MB"``."""
    parcel: Optional[AgParcel] = None
    productivity: Optional[AgProductivity] = None
    cropping: Optional[AgCropping] = None
    soil: Optional[AgSoil] = None
    land_use: Optional[AgLandUse] = None
    drought: Optional[AgDrought] = None
    wetlands: Optional[AgWetlands] = None
    hydrology: Optional[AgHydrology] = None
    parcel_context: Optional[AgParcelContext] = None
    provincial_detail: Optional[AgProvincialDetail] = None
    units: Optional[Dict[str, str]] = None
    meta: Optional[ReportMeta] = None


# --- Energy API models ---


class EnergyParcel(_ReportSection):
    """Parcel block on energy reports."""

    area_ha: Optional[float] = None
    centroid: Optional[LatLng] = None
    geometry: Optional[Union[Polygon, MultiPolygon]] = None
    """GeoJSON when requested with ``include=["geometry", ...]``, else None."""


class EnergyWellCounts(_ReportSection):
    """Well counts by state (regulator or Petrinex basis)."""

    total: Optional[int] = None
    active: Optional[int] = None
    suspended: Optional[int] = None
    abandoned: Optional[int] = None
    orphan: Optional[int] = None
    reclamation_certified: Optional[int] = None
    oil: Optional[int] = None
    gas: Optional[int] = None
    water: Optional[int] = None


class EnergySummaryWells(EnergyWellCounts):
    """Well rollup with the per-source breakdown."""

    primary_source: Optional[str] = None
    """``"regulator"`` or ``"petrinex"``."""
    by_source: Optional[Dict[str, EnergyWellCounts]] = None


class EnergyDominantOperator(OperatorRef):
    """The dominant operator on the parcel with its well share."""

    well_count: Optional[int] = None
    well_share_pct: Optional[float] = None
    share_basis: Optional[str] = None
    """``"regulator_total_wells"`` or ``"petrinex_total_wells"``."""


class EnergySummaryPipelines(_ReportSection):
    """Pipeline rollup on the parcel."""

    segment_count: Optional[int] = None
    length_m_on_parcel: Optional[float] = None


class EnergySummaryFacilities(_ReportSection):
    """Facility rollup on the parcel."""

    count: Optional[int] = None
    categories: List[str] = Field(default_factory=list)


class EnergySummaryOperators(_ReportSection):
    """Operator rollup on the parcel."""

    dominant: Optional[EnergyDominantOperator] = None


class EnergySummary(_ReportSection):
    """Aggregated energy activity on the parcel."""

    wells: Optional[EnergySummaryWells] = None
    pipelines: Optional[EnergySummaryPipelines] = None
    facilities: Optional[EnergySummaryFacilities] = None
    operators: Optional[EnergySummaryOperators] = None
    last_activity_date: Optional[str] = None
    """Date-only fact, ``"YYYY-MM-DD"``."""


class EnergyProductionVolumes(_ReportSection):
    """Trailing-window production volumes."""

    oil_m3: Optional[float] = None
    gas_e3m3: Optional[float] = None
    condensate_m3: Optional[float] = None
    water_m3: Optional[float] = None


class EnergyProduction(_ReportSection):
    """Trailing-12-month Petrinex production."""

    window_months: Optional[int] = None
    last_producing_month: Optional[str] = None
    """Month fact, ``"YYYY-MM"``."""
    volumes: Optional[EnergyProductionVolumes] = None
    has_oil: Optional[bool] = None
    has_gas: Optional[bool] = None
    has_condensate: Optional[bool] = None
    has_water: Optional[bool] = None
    dominant_product: Optional[str] = None
    """``"oil"``, ``"gas"``, ``"condensate"``, or ``None``."""
    producing_well_count: Optional[int] = None


class EnergyTenureRow(_ReportSection):
    """A Crown tenure disposition (uniform row shape, PNG and mineral)."""

    id: Optional[str] = None
    """Disposition slug: plain number for PNG, ``category:number`` for mineral."""
    href: Optional[str] = None
    """``/energy/dispositions/{id}``."""
    tenure_kind: Optional[str] = None
    """``"png"`` or ``"mineral"`` — the row-shape discriminator."""
    province: Optional[str] = None
    disposition_number: Optional[str] = None
    mineral_category: Optional[str] = None
    disposition_type: Optional[str] = None
    disposition_type_raw: Optional[str] = None
    target_substance: Optional[str] = None
    coal_category: Optional[str] = None
    holder: Optional[OperatorRef] = None
    status: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    days_to_expiry: Optional[int] = None
    """Signed: negative means expired; ``None`` means perpetual/no expiry."""
    expiry_state: Optional[str] = None
    """``expired | expires_today | expiring_soon | active | perpetual``."""
    area_ha: Optional[float] = None
    lsd_coverage_pct: Optional[float] = None
    is_transfer_pending: Optional[bool] = None
    overlap_point: Optional[LatLng] = None
    """Point inside the parcel overlap (parcel-scoped rows)."""
    centroid: Optional[LatLng] = None
    """Point of the whole feature (cross-parcel rows)."""


class EnergyWellRow(_ReportSection):
    """A well on the parcel."""

    id: Optional[str] = None
    uwi: Optional[str] = None
    well_name: Optional[str] = None
    licence_number: Optional[str] = None
    status: Optional[str] = None
    """The normalized state the ``?status=`` filter accepts."""
    licence_status_raw: Optional[str] = None
    operator: Optional[OperatorRef] = None
    fluid: Optional[str] = None
    mode: Optional[str] = None
    type: Optional[str] = None
    total_depth_m: Optional[float] = None
    is_orphan: Optional[bool] = None
    is_abandoned: Optional[bool] = None
    is_suspended: Optional[bool] = None
    location: Optional[LatLng] = None


class EnergyPipelineRow(_ReportSection):
    """A pipeline segment crossing the parcel."""

    id: Optional[str] = None
    href: Optional[str] = None
    """``/energy/pipelines/{licence_number}``."""
    licence_number: Optional[str] = None
    segment_id: Optional[str] = None
    operator: Optional[OperatorRef] = None
    status: Optional[str] = None
    segment_status_raw: Optional[str] = None
    substance: Optional[str] = None
    outside_diameter_mm: Optional[float] = None
    max_operating_pressure_kpa: Optional[float] = None
    h2s_pct: Optional[float] = None
    h2s_release_level: Optional[str] = None
    class_location: Optional[str] = None
    pipeline_environment: Optional[str] = None
    length_m_on_parcel: Optional[float] = None
    segment_length_km: Optional[float] = None
    """The segment's own full length in km."""
    overlap_point: Optional[LatLng] = None
    centroid: Optional[LatLng] = None


class EnergyFacilityRow(_ReportSection):
    """A facility on the parcel."""

    id: Optional[str] = None
    facility_name: Optional[str] = None
    category: Optional[str] = None
    sub_type: Optional[str] = None
    sub_code: Optional[str] = None
    status: Optional[str] = None
    facility_status_raw: Optional[str] = None
    licence_number: Optional[str] = None
    operator: Optional[OperatorRef] = None
    licensee: Optional[OperatorRef] = None
    location: Optional[LatLng] = None


class EnergyTenureSection(_ReportSection):
    """``{total, returned, truncated, more, rows}`` envelope of tenure rows."""

    total: int = 0
    returned: int = 0
    truncated: bool = False
    more: Optional[str] = None
    rows: List[EnergyTenureRow] = Field(default_factory=list)


class EnergyWellsSection(_ReportSection):
    """``{total, returned, truncated, more, rows}`` envelope of well rows."""

    total: int = 0
    returned: int = 0
    truncated: bool = False
    more: Optional[str] = None
    rows: List[EnergyWellRow] = Field(default_factory=list)


class EnergyPipelinesSection(_ReportSection):
    """``{total, returned, truncated, more, rows}`` envelope of pipeline rows."""

    total: int = 0
    returned: int = 0
    truncated: bool = False
    more: Optional[str] = None
    rows: List[EnergyPipelineRow] = Field(default_factory=list)


class EnergyFacilitiesSection(_ReportSection):
    """``{total, returned, truncated, more, rows}`` envelope of facility rows."""

    total: int = 0
    returned: int = 0
    truncated: bool = False
    more: Optional[str] = None
    rows: List[EnergyFacilityRow] = Field(default_factory=list)


class EnergyReport(_ReportSection):
    """Per-parcel energy report, keyed at LSD grain.

    A ``None`` section means no data at that location or one source
    degraded (``meta.unavailable`` says which); the rest of the report is
    still trustworthy. Sections are ``None`` when omitted by an
    ``include=`` projection. Array sections are
    ``{total, returned, truncated, more, rows}`` envelopes.
    """

    legal_location: str
    province: Optional[str] = None
    """Uppercase province code: ``"AB" | "SK" | "MB"``."""
    parcel: Optional[EnergyParcel] = None
    summary: Optional[EnergySummary] = None
    production: Optional[EnergyProduction] = None
    tenure: Optional[EnergyTenureSection] = None
    wells: Optional[EnergyWellsSection] = None
    pipelines: Optional[EnergyPipelinesSection] = None
    facilities: Optional[EnergyFacilitiesSection] = None
    alternative_energy: Optional[Dict[str, Any]] = None
    """``{ccs_tenure, geothermal_tenure, ccs_injection_wells}`` envelopes."""
    units: Optional[Dict[str, str]] = None
    meta: Optional[ReportMeta] = None
