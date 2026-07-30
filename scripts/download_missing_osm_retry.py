#!/usr/bin/env python3
"""Retry failed OSM downloads with smaller queries."""
import json, time, urllib.request, urllib.error, os

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX = "44.5,38.4,51.0,42.0"
DATA_DIR = "data/geojson"

def overpass_query(query, name):
    body = "data=" + urllib.parse.quote(query)
    data_bytes = body.encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(OVERPASS_URL, data=data_bytes,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                raw = resp.read().decode("utf-8")
            n = len(raw)
            print(f"  {name}: {n} bytes")
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            print(f"  {name}: HTTP {e.code}: {body}")
            if e.code == 429:
                time.sleep(15)
            elif attempt < 2:
                time.sleep(10)
            else:
                return None
        except Exception as e:
            print(f"  {name}: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                return None
    return None

def osm_to_geojson(osm_json):
    features = []
    for el in osm_json.get("elements", []):
        el_type = el.get("type")
        tags = el.get("tags", {})
        if el_type == "node":
            lon, lat = el.get("lon"), el.get("lat")
        elif "center" in el:
            lon, lat = el["center"]["lon"], el["center"]["lat"]
        elif "bounds" in el:
            b = el["bounds"]
            lon = (b["minlon"] + b["maxlon"]) / 2
            lat = (b["minlat"] + b["maxlat"]) / 2
        else:
            continue
        if lon is None or lat is None:
            continue
        props = {"osm_id": el.get("id"), "osm_type": el_type,
            "name": tags.get("name", ""), "name_az": tags.get("name:az", tags.get("name:en", "")),
            "amenity": tags.get("amenity", ""), "leisure": tags.get("leisure", ""),
            "shop": tags.get("shop", ""), "sport": tags.get("sport", "")}
        features.append({"type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props})
    return {"type": "FeatureCollection", "features": features}

import urllib.parse

# Retry SHOPPING - smaller queries
print("=== Retrying SHOPPING ===")
shopping_queries = [
    ("mall_supermarket", f'[out:json][timeout:120];node["shop"~"mall|supermarket|department_store"]({BBOX});out center;'),
    ("mall_supermarket_ways", f'[out:json][timeout:120];way["shop"~"mall|supermarket|department_store"]({BBOX});out center;'),
    ("marketplace", f'[out:json][timeout:120];node["amenity"="marketplace"]({BBOX});out center;'),
]

all_shopping = {"type": "FeatureCollection", "features": []}
for sname, squery in shopping_queries:
    print(f"  Downloading {sname}...")
    result = overpass_query(squery, sname)
    if result:
        geojson = osm_to_geojson(result)
        n = len(geojson["features"])
        all_shopping["features"].extend(geojson["features"])
        print(f"    Got {n} features")
    time.sleep(3)

with open(f"{DATA_DIR}/osm_shopping.geojson", "w") as f:
    json.dump(all_shopping, f, indent=2)
print(f"  TOTAL shopping: {len(all_shopping['features'])} features")

# Retry SPORTS
print("\n=== Retrying SPORTS ===")
sports_queries = [
    ("leisure", f'[out:json][timeout:120];node["leisure"~"sports_centre|stadium|fitness_centre|swimming_pool|golf_course|pitch|track"]({BBOX});out center;'),
    ("leisure_ways", f'[out:json][timeout:120];way["leisure"~"sports_centre|stadium|fitness_centre|swimming_pool|golf_course|pitch|track"]({BBOX});out center;'),
    ("sport_nodes", f'[out:json][timeout:120];node["sport"]({BBOX});out 2000;'),
]

all_sports = {"type": "FeatureCollection", "features": []}
for sname, squery in sports_queries:
    print(f"  Downloading {sname}...")
    result = overpass_query(squery, sname)
    if result:
        geojson = osm_to_geojson(result)
        n = len(geojson["features"])
        all_sports["features"].extend(geojson["features"])
        print(f"    Got {n} features")
    time.sleep(3)

with open(f"{DATA_DIR}/osm_sports.geojson", "w") as f:
    json.dump(all_sports, f, indent=2)
print(f"  TOTAL sports: {len(all_sports['features'])} features")

print("\n=== Phase 1b Summary ===")
for name in ["osm_shopping", "osm_sports"]:
    with open(f"{DATA_DIR}/{name}.geojson") as f:
        d = json.load(f)
    print(f"  {name}: {len(d.get('features',[]))} features")
