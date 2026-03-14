"""Pydantic models for Township Canada API request and response types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


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


@dataclass
class AutocompleteSuggestion:
    """A single autocomplete suggestion."""

    legal_location: str
    latitude: float
    longitude: float
    survey_system: str
    unit: str
