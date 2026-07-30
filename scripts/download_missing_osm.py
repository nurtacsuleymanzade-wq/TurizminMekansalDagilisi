#!/usr/bin/env python3
"""Phase 1: Download missing OSM categories via Overpass API.
Fixed version - uses proper Accept header for Overpass.
"""
import json, time, urllib.request, urllib.error, os

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX = "44.5,38.4,51.0,42.0"
DATA_DIR = "data/geojson"
os.makedirs(DATA_DIR, exist_ok=True)

QUERIES = {
    "osm_religious": '[out:json][timeout:120];(node["amenity"~"place_of_worship|monastery|shrine"]({bbox});way["amenity"~"place_of_worship|monastery|shrine"]({bbox});node["historic"~"tomb|shrine"]({bbox});way["historic"~"tomb|shrine"]({bbox});node["religion"]({bbox}););out center;',
    "osm_shopping": '[out:json][timeout:120];(node["shop"~"mall|supermarket|department_store"]({bbox});way["shop"~"mall|supermarket|department_store"]({bbox});node["amenity"~"marketplace"]({bbox});way["amenity"~"marketplace"]({bbox}););out center;',
    "osm_sports": '[out:json][timeout:120];(node["leisure"~"sports_centre|stadium|fitness_centre|swimming_pool|golf_course|pitch|track"]({bbox});way["leisure"~"sports_centre|stadium|fitness_centre|swimming_pool|golf_course|pitch|track"]({bbox});node["sport"]({bbox}););out center;',
    "osm_entertainment": '[out:json][timeout:120];(node["amenity"~"cinema|theatre|nightclub|casino|gambling|community_centre"]({bbox});way["amenity"~"cinema|theatre|nightclub|casino|gambling|community_centre"]({bbox}););out center;',
    "osm_hamams": '[out:json][timeout:120];(node["amenity"~"public_bath|hammam|hamam"]({bbox});way["amenity"~"public_bath|hammam|hamam"]({bbox}););out center;',
}

def overpass_query(query, name):
    """Run Overpass query with proper headers."""
    # Build form-encoded body
    body = "data=" + urllib.parse.quote(query)
    data_bytes = body.encode()
    
    for attempt in range(3):
        try:
            req = urllib.request.Request(OVERPASS_URL, data=data_bytes,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json, text/plain, */*",
                    "User-Agent": "TurizminMekansalDagilisi/1.0"
                })
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode("utf-8")
            print(f"  {name}: Downloaded {len(raw)} bytes, first 50: {raw[:50].strip()}")
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            if e.code == 429:
                wait = 10 * (attempt + 1)
                print(f"  {name}: 429 rate limited, waiting {wait}s...")
                time.sleep(wait)
            elif e.code == 406:
                print(f"  {name}: 406 Not Acceptable - trying without Accept header")
                # Try again without the accept header
                try:
                    req2 = urllib.request.Request(OVERPASS_URL, data=data_bytes,
                        headers={"Content-Type": "application/x-www-form-urlencoded"})
                    with urllib.request.urlopen(req2, timeout=180) as resp:
                        raw = resp.read().decode("utf-8")
                    print(f"  {name}: Downloaded {len(raw)} bytes (retry ok)")
                    return json.loads(raw)
                except Exception as e2:
                    print(f"  {name}: Retry also failed: {e2}")
                    return None
            else:
                print(f"  {name}: HTTP {e.code}: {body}")
                return None
        except Exception as e:
            print(f"  {name}: Error: {e}")
            if attempt < 2:
                time.sleep(5)
            else:
                return None
    return None

def osm_to_geojson(osm_json):
    """Convert Overpass JSON response to GeoJSON FeatureCollection."""
    features = []
    elements = osm_json.get("elements", [])
    for el in elements:
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
        
        props = {
            "osm_id": el.get("id"),
            "osm_type": el_type,
            "name": tags.get("name", ""),
            "name_az": tags.get("name:az", tags.get("name:en", "")),
            "amenity": tags.get("amenity", ""),
            "leisure": tags.get("leisure", ""),
            "shop": tags.get("shop", ""),
            "religion": tags.get("religion", ""),
            "historic": tags.get("historic", ""),
            "sport": tags.get("sport", ""),
        }
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": props
        })
    
    return {"type": "FeatureCollection", "features": features}

# Main
import urllib.parse

for name, query_template in QUERIES.items():
    outpath = os.path.join(DATA_DIR, f"{name}.geojson")
    if os.path.exists(outpath):
        with open(outpath) as f:
            existing = json.load(f)
        print(f"{name}: Already exists ({len(existing.get('features',[]))} features), skipping")
        continue
    
    query = query_template.format(bbox=BBOX)
    print(f"\nDownloading {name}...")
    result = overpass_query(query, name)
    if result is None:
        print(f"  FAILED - will create empty file")
        geojson = {"type": "FeatureCollection", "features": []}
    else:
        geojson = osm_to_geojson(result)
    
    with open(outpath, "w") as f:
        json.dump(geojson, f, indent=2)
    print(f"  Saved {len(geojson['features'])} features to {outpath}")
    time.sleep(2)

print("\n=== Phase 1 Summary ===")
total = 0
for name in QUERIES:
    path = os.path.join(DATA_DIR, f"{name}.geojson")
    if os.path.exists(path):
        with open(path) as f:
            d = json.load(f)
        n = len(d.get('features',[]))
        total += n
        print(f"  {name}: {n} features")
    else:
        print(f"  {name}: MISSING")
print(f"TOTAL new features: {total}")
