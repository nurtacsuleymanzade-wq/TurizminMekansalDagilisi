#!/usr/bin/env python3
"""Build the public, static Nova Atlas data bundle.

The source directory is a local/VPS derivative cache and is never committed.
Only cartographic fields required by the public interactive map are retained;
Google virtual-fieldwork identifiers, links, timestamps and nearby-service
payloads are deliberately excluded.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


COPY_LAYERS = {
    "country",
    "rayons",
    "settlements_major",
    "roads_primary",
    "roads_secondary",
    "roads_local",
    "railways",
    "rail_stations",
    "airports",
    "bus_terminals",
    "rivers_major",
    "lakes_reservoirs",
    "protected_areas",
    "natural",
    "cultural",
    "accommodation",
    "food",
}

ATLAS_LAYERS = {"atlas_core", "atlas_core_country"}

ATLAS_FIELDS = {
    "poi_id",
    "name_az",
    "label",
    "rayon",
    "rayon_id",
    "thesis_group",
    "thesis_subtype",
    "verification_status",
    "official_status",
    "source_role",
    "source_primary",
    "source_secondary",
    "display_rank",
    "icon_id",
    "elevation_m",
    "slope_deg",
    "elevation_zone",
    "terrain_context",
    "landcover_class",
    "nearest_airport_km",
    "nearest_bus_terminal_km",
    "nearest_rail_station_km",
    "nearest_protected_area",
    "nearest_river",
    "nearest_river_distance_m",
    "coastal_distance_km",
    "inside_protected_area",
    "osm_route_distance_km",
    "osm_drive_time_min",
    "osm_route_status",
    "access_mode_status",
    "official_evidence_source",
    "semantic_source_url",
    "heritage_source_url",
}


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write("\n")


def sanitise_atlas(source: Path, destination: Path) -> dict:
    data = read_json(source)
    for feature in data.get("features", []):
        properties = feature.get("properties") or {}
        feature["properties"] = {
            key: properties[key]
            for key in ATLAS_FIELDS
            if key in properties and properties[key] not in (None, "")
        }
    write_json(destination, data)
    return data


def search_record(feature: dict) -> dict | None:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates")
    if geometry.get("type") != "Point" or not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    properties = feature.get("properties") or {}
    label = properties.get("label") or properties.get("name_az") or properties.get("name") or properties.get("name_en")
    if not label:
        return None
    return {
        "label": label,
        "rayon": properties.get("rayon") or properties.get("official_city") or "",
        "group": properties.get("thesis_group") or "TRANSPORT",
        "subtype": properties.get("thesis_subtype") or properties.get("type") or "",
        "status": properties.get("verification_status") or properties.get("operational_status") or "",
        "source_role": properties.get("source_role") or ("OFFICIAL_TRANSPORT" if properties.get("official_verified") else ""),
        "lon": coordinates[0],
        "lat": coordinates[1],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not (source_dir / "manifest.json").is_file():
        raise SystemExit(f"Missing source manifest: {source_dir / 'manifest.json'}")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_manifest = read_json(source_dir / "manifest.json")
    public_layers: dict[str, dict] = {}
    loaded: dict[str, dict] = {}

    for layer_id, info in source_manifest.get("layers", {}).items():
        if layer_id == "physical_relief":
            relief_name = info["file"]
            shutil.copy2(source_dir / relief_name, output_dir / relief_name)
            public_layers[layer_id] = dict(info)
            continue
        if layer_id not in COPY_LAYERS | ATLAS_LAYERS:
            continue
        source_file = source_dir / info["file"]
        output_file = output_dir / info["file"]
        if layer_id in ATLAS_LAYERS:
            loaded[layer_id] = sanitise_atlas(source_file, output_file)
        else:
            shutil.copy2(source_file, output_file)
        public_layers[layer_id] = dict(info)

    search: list[dict] = []
    search_keys: set[tuple[str, str, float, float]] = set()
    searchable = ["atlas_core", "natural", "cultural", "accommodation", "food", "airports", "rail_stations", "bus_terminals", "settlements_major"]
    for layer_id in searchable:
        info = public_layers.get(layer_id)
        if not info:
            continue
        data = loaded.get(layer_id) or read_json(output_dir / info["file"])
        for feature in data.get("features", []):
            item = search_record(feature)
            if item:
                key = (
                    str(item["label"]).casefold(),
                    str(item["rayon"]).casefold(),
                    round(float(item["lon"]), 5),
                    round(float(item["lat"]), 5),
                )
                if key not in search_keys:
                    search_keys.add(key)
                    search.append(item)
    write_json(output_dir / "search.json", search)

    public_manifest = {
        "version": 2,
        "source_role": "PUBLIC_CARTOGRAPHIC_DERIVATIVE",
        "privacy_note": "Google virtual-fieldwork identifiers and private validation payloads are excluded.",
        "layers": public_layers,
        "stats": {
            "atlas_core": public_layers.get("atlas_core", {}).get("count", 0),
            "atlas_core_country": public_layers.get("atlas_core_country", {}).get("count", 0),
            "natural": public_layers.get("natural", {}).get("count", 0),
            "cultural": public_layers.get("cultural", {}).get("count", 0),
            "accommodation": public_layers.get("accommodation", {}).get("count", 0),
            "food": public_layers.get("food", {}).get("count", 0),
            "search_records": len(search),
            "transport": {
                "airports": public_layers.get("airports", {}).get("count", 0),
                "rail_stations": public_layers.get("rail_stations", {}).get("count", 0),
                "bus_terminals": public_layers.get("bus_terminals", {}).get("count", 0),
            },
        },
    }
    write_json(output_dir / "manifest.json", public_manifest)
    print(json.dumps({"layers": len(public_layers), "search_records": len(search)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
