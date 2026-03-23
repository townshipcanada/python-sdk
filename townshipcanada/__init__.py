"""Township Canada Python SDK — Canadian legal land description coordinate conversion.

Usage::

    from townshipcanada import TownshipCanada

    tc = TownshipCanada("your_api_key")
    result = tc.search("NW-36-42-3-W5")
    print(result.latitude, result.longitude)
"""

from .client import AsyncTownshipCanada, TownshipCanada
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
    AutocompleteSuggestion,
    BatchResult,
    Feature,
    FeatureCollection,
    FeatureProperties,
    MultiPolygon,
    Point,
    Polygon,
    SearchResult,
)

__all__ = [
    "TownshipCanada",
    "AsyncTownshipCanada",
    "TownshipCanadaError",
    "AuthenticationError",
    "NotFoundError",
    "PayloadTooLargeError",
    "RateLimitError",
    "ServerError",
    "ValidationError",
    "SearchResult",
    "BatchResult",
    "AutocompleteSuggestion",
    "FeatureCollection",
    "Feature",
    "FeatureProperties",
    "Point",
    "Polygon",
    "MultiPolygon",
]

from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("townshipcanada")
except Exception:
    __version__ = "0.0.0-dev"
