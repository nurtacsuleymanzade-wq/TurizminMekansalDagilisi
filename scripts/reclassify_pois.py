#!/usr/bin/env python3
"""Phase 2: Reclassify all POIs into 7 categories with region assignment."""
import json, os, csv, glob

DATA_DIR = "data/geojson"
PROCESSED_DIR = "data/processed"
SCRIPTS_DIR = "scripts"
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# Category configuration
CATEGORY_CONFIG = {
    "Yeme-İçme": {"color": "#e74c3c", "marker": "restaurant", "icon_emoji": "🍽️", "sort_order": 1},
    "Otel/Konaklama": {"color": "#3498db", "marker": "lodging", "icon_emoji": "🏨", "sort_order": 2},
    "Tarihi-Kültürel": {"color": "#9b59b6", "marker": "museum", "icon_emoji": "🏛️", "sort_order": 3},
    "Spor": {"color": "#2ecc71", "marker": "sports", "icon_emoji": "⚽", "sort_order": 4},
    "Alışveriş-Eğlence": {"color": "#f39c12", "marker": "shopping", "icon_emoji": "🛍️", "sort_order": 5},
    "Park-Plaj-Doğa": {"color": "#1abc9c", "marker": "park", "icon_emoji": "🏖️", "sort_order": 6},
    "Dini Yerler": {"color": "#e67e22", "marker": "place_of_worship", "icon_emoji": "🕌", "sort_order": 7}
}

# Map source files to categories with subcategory extraction
SOURCE_MAP = {
    "osm_food_drink": ("Yeme-İçme", lambda tags: tags.get("amenity", tags.get("cuisine", "Restoran"))),
    "osm_accommodation": ("Otel/Konaklama", lambda tags: tags.get("tourism", tags.get("amenity", "Konaklama"))),
    "osm_tourism_historic": ("Tarihi-Kültürel", lambda tags: tags.get("historic", tags.get("tourism", "Tarihi"))),
    "osm_cultural": ("Tarihi-Kültürel", lambda tags: tags.get("amenity", "Kültür Merkezi")),
    "osm_attractions": ("Tarihi-Kültürel", lambda tags: tags.get("tourism", tags.get("leisure", "Turistik"))),
    "osm_hamams": ("Tarihi-Kültürel", lambda tags: "Hamam"),
    "osm_natural": ("Park-Plaj-Doğa", lambda tags: tags.get("leisure", tags.get("natural", "Doğa Alanı"))),
    "osm_religious": ("Dini Yerler", lambda tags: tags.get("amenity", tags.get("religion", "Dini Yapı"))),
    "osm_shopping": ("Alışveriş-Eğlence", lambda tags: tags.get("shop", "Alışveriş")),
    "osm_entertainment": ("Alışveriş-Eğlence", lambda tags: tags.get("amenity", "Eğlence")),
    "osm_sports": ("Spor", lambda tags: tags.get("leisure", tags.get("sport", "Spor Tesisi"))),
    "osm_transportation_hubs": ("Alışveriş-Eğlence", lambda tags: "Ulaşım"),
}

def load_geojson(path):
    """Load a GeoJSON file safely."""
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found")
        return {"type": "FeatureCollection", "features": []}
    with open(path) as f:
        d = json.load(f)
    print(f"  {os.path.basename(path)}: {len(d.get('features', []))} features")
    return d

def get_subcategory(tags, sub_func):
    """Get subcategory from tags, handle missing keys."""
    try:
        val = sub_func(tags)
        if not val:
            return "Diğer"
        return str(val).capitalize()
    except:
        return "Diğer"

def assign_region(feature, region_gdf):
    """Assign economic region using point-in-polygon."""
    from shapely.geometry import Point, shape as shapely_shape
    
    coords = feature["geometry"]["coordinates"]
    point = Point(coords[0], coords[1])
    
    for idx, row in region_gdf.iterrows():
        if row["geometry"].contains(point):
            return row.get("er_az", row.get("er_en", "Bilinmeyen"))
    
    # Fallback: check closest
    min_dist = float("inf")
    closest = "Bilinmeyen"
    for idx, row in region_gdf.iterrows():
        dist = row["geometry"].distance(point)
        if dist < min_dist:
            min_dist = dist
            closest = row.get("er_az", row.get("er_en", "Bilinmeyen"))
    return closest

# Load economic regions for spatial join
print("Loading administrative boundaries...")
try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
    region_gdf = gpd.read_file(f"{DATA_DIR}/aze_economicregion.geojson")
    print(f"  Economic regions loaded: {len(region_gdf)}")
except Exception as e:
    print(f"  WARNING: Could not load regions: {e}")
    HAS_GEOPANDAS = False
    region_gdf = None

# Also try to load rayon boundaries for fallback
try:
    rayon_gdf = gpd.read_file(f"{DATA_DIR}/azerbaijan_rayon_boundaries.geojson")
    print(f"  Rayon boundaries loaded: {len(rayon_gdf)}")
except:
    rayon_gdf = None

# Process all source files
print("\nLoading and classifying all POI sources...")
all_features = []
category_counts = {}  # {category: total}
region_category_counts = {}  # {(region, category): count}

for src_name, (category, sub_func) in SOURCE_MAP.items():
    geojson_path = f"{DATA_DIR}/{src_name}.geojson"
    data = load_geojson(geojson_path)
    
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        name = props.get("name", props.get("name_az", ""))
        if not name:
            name = f"{category} #{feat['properties'].get('osm_id', '')}"
        
        subcategory = get_subcategory(props, sub_func)
        
        # Get coordinates safely
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        lon, lat = coords[0], coords[1]
        
        new_props = {
            "name": name,
            "category": category,
            "subcategory": subcategory,
            "source": src_name,
            "osm_id": props.get("osm_id", ""),
            "region": "",
            "rayon": ""
        }
        
        new_feat = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": new_props
        }
        all_features.append(new_feat)
        
        # Count
        category_counts[category] = category_counts.get(category, 0) + 1

print(f"\nTotal features loaded: {len(all_features)}")

# Also include all_tourism_points (existing) — match to categories
print("\nLoading existing all_tourism_points...")
try:
    tourism = load_geojson(f"{DATA_DIR}/all_tourism_points.geojson")
    category_map = {
        "Otel": "Otel/Konaklama",
        "Tarih": "Tarihi-Kültürel",
        "Kültür": "Tarihi-Kültürel",
        "Doğa": "Park-Plaj-Doğa",
        "doga": "Park-Plaj-Doğa",
        "nature": "Park-Plaj-Doğa",
        "Spor": "Spor",
        "spor": "Spor",
        "spor aktiviteleri": "Spor",
        "Yeme": "Yeme-İçme",
        "Yiyecek": "Yeme-İçme",
        "Alışveriş": "Alışveriş-Eğlence",
        "Eğlence": "Alışveriş-Eğlence",
    }
    
    for feat in tourism.get("features", []):
        props = feat.get("properties", {})
        old_cat = props.get("category", "")
        
        # Map old category to new
        matched = False
        for old_key, new_cat in category_map.items():
            if old_key.lower() in old_cat.lower():
                category = new_cat
                matched = True
                break
        
        if not matched:
            continue  # Skip unmapped from existing dataset
        
        name = props.get("name", "")
        if not name:
            name = f"{category} #{props.get('osm_id', '')}"
        
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        lon, lat = coords[0], coords[1]
        
        # Check if this POI already exists (by coordinates)
        is_duplicate = False
        for existing in all_features:
            ec = existing["geometry"]["coordinates"]
            if abs(ec[0] - lon) < 0.001 and abs(ec[1] - lat) < 0.001:
                is_duplicate = True
                break
        
        if is_duplicate:
            continue
        
        new_props = {
            "name": name,
            "category": category,
            "subcategory": old_cat,
            "source": "all_tourism_points",
            "osm_id": props.get("osm_id", ""),
            "region": "",
            "rayon": ""
        }
        all_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": new_props
        })
        category_counts[category] = category_counts.get(category, 0) + 1
except Exception as e:
    print(f"  Skipping all_tourism_points: {e}")

print(f"\nTotal after dedup: {len(all_features)}")

# Spatial join for region assignment
print("\nAssigning regions via spatial join...")
if HAS_GEOPANDAS and region_gdf is not None:
    from shapely.geometry import Point
    
    for i, feat in enumerate(all_features):
        coords = feat["geometry"]["coordinates"]
        point = Point(coords[0], coords[1])
        
        # Check economic regions
        found_region = ""
        for idx, row in region_gdf.iterrows():
            if row["geometry"].contains(point):
                found_region = row.get("er_az", row.get("er_en", ""))
                break
        
        # Fallback to rayon
        if not found_region and rayon_gdf is not None:
            for idx, row in rayon_gdf.iterrows():
                if row["geometry"].contains(point):
                    found_region = row.get("adm1_name1", row.get("adm1_name", ""))
                    feat["properties"]["rayon"] = found_region
                    break
        
        feat["properties"]["region"] = found_region if found_region else "Bilinmeyen"
        
        # Count
        region = feat["properties"]["region"]
        cat = feat["properties"]["category"]
        region_category_counts[(region, cat)] = region_category_counts.get((region, cat), 0) + 1
        
        if (i + 1) % 5000 == 0:
            print(f"  Processed {i+1}/{len(all_features)}...")

# Save unified GeoJSON
output_geojson = f"{DATA_DIR}/all_pois_reclassified.geojson"
print(f"\nSaving unified GeoJSON to {output_geojson}...")
output = {"type": "FeatureCollection", "features": all_features}
with open(output_geojson, "w") as f:
    json.dump(output, f, indent=2)
print(f"  Saved {len(all_features)} features")

# Save category counts
print("\nSaving category counts...")
csv_path = f"{PROCESSED_DIR}/poi_category_counts.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Region", "Category", "Count"])
    for (region, cat), count in sorted(region_category_counts.items()):
        writer.writerow([region, cat, count])
    
    # Also write totals per category
    writer.writerow([])
    writer.writerow(["TOTAL", "", ""])
    for cat, count in sorted(category_counts.items(), key=lambda x: CATEGORY_CONFIG.get(x[0], {}).get("sort_order", 99)):
        writer.writerow([cat, "Toplam", count])

print(f"  Saved to {csv_path}")

# Save category config
config_path = f"{SCRIPTS_DIR}/category_config.json"
with open(config_path, "w") as f:
    json.dump(CATEGORY_CONFIG, f, indent=2, ensure_ascii=False)
print(f"  Category config saved to {config_path}")

# Summary
print("\n" + "="*60)
print("PHASE 2 COMPLETE - POI CLASSIFICATION SUMMARY")
print("="*60)
total = sum(category_counts.values())
print(f"TOTAL POIs: {total:,}")
print()
for cat, count in sorted(category_counts.items(), key=lambda x: CATEGORY_CONFIG.get(x[0], {}).get("sort_order", 99)):
    cfg = CATEGORY_CONFIG.get(cat, {})
    print(f"  {cfg.get('icon_emoji', '')} {cat}: {count:,} POIs (color: {cfg.get('color', '')})")
print(f"\n  Total: {total:,} POIs across 7 categories")
print(f"\nFiles created:")
print(f"  {output_geojson}")
print(f"  {csv_path}")
print(f"  {config_path}")
