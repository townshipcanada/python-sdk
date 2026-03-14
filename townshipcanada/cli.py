"""Command-line interface for the Township Canada SDK.

Usage::

    township convert "NW-36-42-3-W5"
    township convert "A-2-F/93-P-8"
    township convert "Lot 2 Con 4 Osprey"
    township reverse -- -114.654321 52.123456
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .client import TownshipCanada
from .exceptions import TownshipCanadaError


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="township",
        description="Convert Canadian legal land descriptions to GPS coordinates.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- convert ---
    convert_parser = subparsers.add_parser(
        "convert",
        help="Convert a legal land description to GPS coordinates.",
    )
    convert_parser.add_argument(
        "location",
        help='Legal land description (e.g. "NW-36-42-3-W5")',
    )
    convert_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON",
    )

    # --- reverse ---
    reverse_parser = subparsers.add_parser(
        "reverse",
        help="Find the legal land description at GPS coordinates.",
    )
    reverse_parser.add_argument("longitude", type=float, help="Longitude")
    reverse_parser.add_argument("latitude", type=float, help="Latitude")
    reverse_parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON",
    )

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    api_key = os.environ.get("TOWNSHIP_API_KEY") or os.environ.get("TOWNSHIP_CANADA_API_KEY")
    if not api_key:
        print(
            "Error: Set TOWNSHIP_API_KEY or TOWNSHIP_CANADA_API_KEY environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = TownshipCanada(api_key)

    try:
        if args.command == "convert":
            result = client.search(args.location)
        else:
            result = client.reverse(args.longitude, args.latitude)

        if args.output_json:
            print(
                json.dumps(
                    {
                        "legal_location": result.legal_location,
                        "latitude": result.latitude,
                        "longitude": result.longitude,
                        "province": result.province,
                        "survey_system": result.survey_system,
                        "unit": result.unit,
                    },
                    indent=2,
                )
            )
        else:
            print(f"{result.latitude}, {result.longitude}")
            print(f"  Location:  {result.legal_location}")
            print(f"  Province:  {result.province}")
            print(f"  System:    {result.survey_system}")
            print(f"  Unit:      {result.unit}")

    except TownshipCanadaError as exc:
        print(f"Error: {exc.message}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
