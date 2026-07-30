#!/usr/bin/env python3
"""
TurizminMekansalDagilisi — Data Processing Pipeline
Aggregates all GeoJSON data by rayon, creates chart-ready datasets.
"""

import os, json, csv, math
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path("/tmp/TurizminMekansalDagilisi")
GEOJSON_DIR = BASE / "data" / "geojson"
PROCESSED_DIR = BASE / "data" / "processed"
PUBLIC_DATA = BASE

os.makedirs(PROCESSED_DIR, exist_ok=True)

print("=" * 60)
print("TURİZMİN MEKANSAL DAĞILIŞI — Data Processing Pipeline")
print("=" * 60)

# Rayon coordinates (centroids) for spatial analysis
# Generated from OSM reference data
RAYON_COORDS = {
    "Absheron": (49.85, 40.45), "Agdam": (46.95, 40.05), "Agdash": (47.47, 40.63),
    "Aghjabadi": (47.37, 40.05), "Agstafa": (45.45, 41.12), "Agsu": (48.38, 40.57),
    "Astara": (48.87, 38.43), "Babek": (45.45, 39.15), "Balakan": (46.78, 41.73),
    "Barda": (47.13, 40.38), "Beylagan": (47.62, 39.78), "Bilasuvar": (48.53, 39.47),
    "Dashkasan": (46.08, 40.52), "Fuzuli": (47.17, 39.58), "Gadabay": (45.80, 40.57),
    "Goranboy": (46.78, 40.60), "Goychay": (47.73, 40.65), "Goygol": (46.33, 40.58),
    "Hajigabul": (48.93, 40.03), "Imishli": (48.07, 39.87), "Ismayilli": (48.15, 40.78),
    "Jabrayil": (47.00, 39.40), "Jalilabad": (48.57, 39.20), "Julfa": (45.57, 38.95),
    "Kalbajar": (46.03, 40.10), "Khachmaz": (48.80, 41.47), "Khizi": (49.12, 40.90),
    "Khojaly": (46.80, 39.90), "Kurdamir": (48.17, 40.33), "Lachin": (46.37, 39.63),
    "Lankaran": (48.83, 38.75), "Lerik": (48.42, 38.78), "Masally": (48.68, 39.03),
    "Neftchala": (49.25, 39.35), "Oghuz": (47.57, 41.07), "Ordubad": (45.97, 38.90),
    "Qabala": (47.85, 40.98), "Qakh": (46.92, 41.42), "Qazakh": (45.37, 41.10),
    "Quba": (48.50, 41.37), "Qubadli": (46.50, 39.35), "Qusar": (48.40, 41.43),
    "Saatly": (48.50, 39.93), "Sabirabad": (48.48, 40.00), "Salyan": (48.98, 39.60),
    "Samukh": (46.42, 40.95), "Shabran": (48.87, 41.22), "Shahbuz": (45.55, 39.40),
    "Shamakhi": (48.93, 40.63), "Shamkir": (46.02, 40.83), "Sharur": (45.15, 39.55),
    "Shusha": (46.75, 39.75), "Siazan": (49.07, 41.08), "Tartar": (46.85, 40.33),
    "Tovuz": (45.62, 40.97), "Ujar": (47.65, 40.52), "Yardimli": (48.23, 38.90),
    "Yevlakh": (47.15, 40.62), "Zangilan": (46.65, 39.08), "Zaqatala": (46.65, 41.63),
    "Zardab": (47.72, 40.22),
    # Cities
    "Baku": (49.87, 40.41), "Ganja": (46.36, 40.68), "Mingachevir": (47.05, 40.77),
    "Naftalan": (46.82, 40.50), "Nakhchivan": (45.42, 39.20), "Shaki": (47.17, 41.20),
    "Shirvan": (48.92, 39.93), "Sumqayit": (49.67, 40.58),
    # Missing border rayons
    "Sedarak": (44.88, 39.70), "Kangarli": (45.17, 39.45),
}

# ─── 1. Load & Aggregate Existing Tourism Points ───────────────────────

def load_all_points():
    """Load all GeoJSON point files and aggregate by rayon"""
    all_features = []
    categories = {}
    
    for f in sorted(GEOJSON_DIR.glob("0*_*.geojson")):
        data = json.loads(f.read_text())
        cat_name = list(categories.keys())[0] if categories else "unknown"
        # Extract category from filename
        name_map = {
            "01_oteller": "Otel", "02_tarihi_anitlar": "Tarihi_Anit",
            "03_diger_tesisler": "Diger_Tesis", "04_ulasim": "Ulasim",
            "05_doga_alanlari": "Doga_Alani", "06_kultur_merkezleri": "Kultur_Merkezi",
            "07_turizm_bolgeleri": "Turizm_Bolgesi", "08_destinasyonlar": "Destinasyon"
        }
        for key, cat in name_map.items():
            if key in f.stem:
                categories[cat] = len(data.get("features", []))
                break
        
        for feat in data.get("features", []):
            feat["_source_file"] = f.name
            all_features.append(feat)
    
    print(f"\n1. LOADED: {len(all_features)} features across {len(categories)} categories")
    for cat, cnt in sorted(categories.items()):
        print(f"   {cat}: {cnt}")
    
    return all_features, categories


def assign_rayon_approximate(lon, lat):
    """Assign a point to a rayon based on nearest centroid (rough spatial join)."""
    min_dist = float("inf")
    best_rayon = "Unknown"
    
    for rayon, (rx, ry) in RAYON_COORDS.items():
        # Simple Euclidean distance (degrees) - approximate
        dist = math.sqrt((lon - rx)**2 + (lat - ry)**2)
        if dist < min_dist:
            min_dist = dist
            best_rayon = rayon
    
    return best_rayon, min_dist


def aggregate_by_rayon(features):
    """Aggregate all features by rayon and category. Creates multiple output files."""
    
    # Count features by (rayon, category)
    rayon_cat = Counter()
    rayon_total = Counter()
    all_coords = []
    
    for feat in features:
        geom = feat.get("geometry", {})
        if geom.get("type") == "Point":
            coords = geom.get("coordinates", [])
        elif geom.get("type") in ["MultiPoint", "LineString", "Polygon"]:
            coords = geom.get("coordinates", [None, None])
            if isinstance(coords, list) and coords and isinstance(coords[0], list):
                coords = coords[0]  # First point as approximate
                if isinstance(coords, list) and len(coords) >= 2:
                    coords = [coords[0], coords[1]]
                else:
                    coords = [None, None]
        else:
            coords = [None, None]
        
        if coords and len(coords) >= 2 and coords[0] is not None and coords[1] is not None:
            lon, lat = float(coords[0]), float(coords[1])
            rayon, dist = assign_rayon_approximate(lon, lat)
            cat = feat.get("properties", {}).get("category", feat.get("_source_file", "unknown"))
            # Clean category name
            cat_clean = cat.replace(".geojson", "").split("_")[-1] if "_" in str(cat) else str(cat)
            # Map to clean name
            cat_clean = cat_clean.replace("Otel", "Otel").replace("Tarihi", "Tarihi_Anit")
            
            rayon_cat[(rayon, cat)] += 1
            rayon_total[rayon] += 1
            all_coords.append({"rayon": rayon, "lon": lon, "lat": lat, "category": cat})
    
    print(f"\n2. AGGREGATED by rayon:")
    print(f"   Total rayons with data: {len(rayon_total)}")
    print(f"   Top 10 rayons by feature count:")
    for rayon, cnt in rayon_total.most_common(10):
        print(f"     {rayon}: {cnt} features")
    
    # Create rayon × category matrix
    all_cats = sorted(set(c for (r, c) in rayon_cat.keys()))
    all_rayons = sorted(RAYON_COORDS.keys())
    
    matrix_rows = []
    for rayon in all_rayons:
        row = {"rayon": rayon, "total": rayon_total.get(rayon, 0)}
        for cat in all_cats:
            row[cat] = rayon_cat.get((rayon, cat), 0)
        # Add coords
        if rayon in RAYON_COORDS:
            row["lon"] = RAYON_COORDS[rayon][0]
            row["lat"] = RAYON_COORDS[rayon][1]
        matrix_rows.append(row)
    
    df = pd.DataFrame(matrix_rows)
    df.to_csv(PROCESSED_DIR / "rayon_feature_matrix.csv", index=False)
    print(f"\n   Saved: rayon_feature_matrix.csv ({len(df)} rayons × {len(all_cats)} categories)")
    
    # Create long-format for Chart.js
    long_rows = []
    for row in matrix_rows:
        if row["total"] > 0:
            for cat in all_cats:
                if row[cat] > 0:
                    long_rows.append({
                        "rayon": row["rayon"],
                        "category": cat,
                        "count": row[cat],
                        "lon": row.get("lon", ""),
                        "lat": row.get("lat", "")
                    })
    
    lf = pd.DataFrame(long_rows)
    lf.to_csv(PROCESSED_DIR / "rayon_category_counts.csv", index=False)
    print(f"   Saved: rayon_category_counts.csv ({len(lf)} rows)")
    
    return df, all_coords


# ─── 2. Create Spatial Analysis Data ──────────────────────────────────────

def compute_hotspot_analysis(df, all_coords):
    """Compute simple hotspot analysis (Gettis-Ord Gi* style using feature density)"""
    print("\n3. SPATIAL ANALYSIS:")
    
    # Calculate feature density per rayon (features per unit area proxy)
    # Since we don't have exact rayon areas, use feature count as base
    mean_count = df["total"].mean()
    std_count = df["total"].std()
    
    hotspot_rows = []
    for _, row in df.iterrows():
        rayon = row["rayon"]
        count = row["total"]
        
        # Z-score approximation
        if std_count > 0:
            z_score = (count - mean_count) / std_count
        else:
            z_score = 0
        
        # Classification
        if count == 0:
            classification = "No Data"
            confidence = 0
        elif z_score > 1.5:
            classification = "Hot Spot (High)"
            confidence = min(0.99, (z_score - 1.5) / 3)
        elif z_score > 0.5:
            classification = "Warm Spot"
            confidence = min(0.8, (z_score - 0.5) / 2)
        elif z_score < -0.5:
            classification = "Cold Spot"
            confidence = min(0.8, (abs(z_score) - 0.5) / 2)
        else:
            classification = "Not Significant"
            confidence = 0
        
        hotspot_rows.append({
            "rayon": rayon,
            "feature_count": count,
            "z_score": round(z_score, 2),
            "classification": classification,
            "confidence": round(confidence, 2),
            "lon": row.get("lon", ""),
            "lat": row.get("lat", "")
        })
    
    hf = pd.DataFrame(hotspot_rows)
    hf.to_csv(PROCESSED_DIR / "hotspot_analysis.csv", index=False)
    print(f"   Saved: hotspot_analysis.csv")
    
    # Print hot/cold spots
    hot = hf[hf["classification"] == "Hot Spot (High)"]
    cold = hf[hf["classification"] == "Cold Spot"]
    print(f"   Hot spots: {len(hot)} rayons")
    for _, r in hot.iterrows():
        print(f"     {r['rayon']}: {int(r['feature_count'])} features (z={r['z_score']})")
    print(f"   Cold spots: {len(cold)} rayons")
    for _, r in cold.iterrows():
        print(f"     {r['rayon']}: {int(r['feature_count'])} features (z={r['z_score']})")
    
    return hf


def create_diversity_analysis(df):
    """Compute tourism diversity index per rayon (Simpson index)"""
    print("\n4. DIVERSITY ANALYSIS:")
    cat_cols = [c for c in df.columns if c not in ["rayon", "total", "lon", "lat"]]
    
    div_rows = []
    for _, row in df.iterrows():
        rayon = row["rayon"]
        counts = [row[c] for c in cat_cols if row[c] > 0]
        total = row["total"]
        
        if total > 0 and len(counts) > 1:
            # Simpson diversity index: 1 - sum(pi^2)
            pi_sq = sum((c/total)**2 for c in counts)
            diversity = 1 - pi_sq
        elif total > 0:
            diversity = 0
        else:
            diversity = 0
        
        n_categories = sum(1 for c in cat_cols if row[c] > 0)
        
        div_rows.append({
            "rayon": rayon,
            "total_features": int(total),
            "category_count": n_categories,
            "simpson_index": round(diversity, 3),
            "lon": row.get("lon", ""),
            "lat": row.get("lat", "")
        })
    
    df_div = pd.DataFrame(div_rows)
    df_div.to_csv(PROCESSED_DIR / "diversity_index.csv", index=False)
    print(f"   Saved: diversity_index.csv")
    
    # Top diverse
    top = df_div.sort_values("simpson_index", ascending=False).head(10)
    print(f"   Top 10 most diverse tourism zones:")
    for _, r in top.iterrows():
        print(f"     {r['rayon']}: Simpson={r['simpson_index']}, {int(r['category_count'])} categories, {int(r['total_features'])} features")
    
    return df_div


def create_category_shares(df):
    """Calculate percentage share of each category per rayon"""
    cat_cols = [c for c in df.columns if c not in ["rayon", "total", "lon", "lat"]]
    
    share_rows = []
    for _, row in df.iterrows():
        rayon = row["rayon"]
        total = row["total"]
        if total == 0:
            continue
        for cat in cat_cols:
            val = row[cat]
            if val > 0:
                share_rows.append({
                    "rayon": rayon,
                    "category": cat,
                    "count": int(val),
                    "share_pct": round(val / total * 100, 1),
                    "lon": row.get("lon", ""),
                    "lat": row.get("lat", "")
                })
    
    df_s = pd.DataFrame(share_rows)
    df_s.to_csv(PROCESSED_DIR / "category_shares.csv", index=False)
    print(f"\n5. CATEGORY SHARES: Saved {len(df_s)} rows")


# ─── 3. Create JSON data files for website ─────────────────────────────────

def create_website_json_data(all_categories):
    """Create JSON files that the website JavaScript can consume directly"""
    print("\n6. Creating website data files...")
    
    # Load hotspot data
    hotspot = pd.read_csv(PROCESSED_DIR / "hotspot_analysis.csv")
    
    # Create GeoJSON of hotspot points
    features = []
    for _, row in hotspot.iterrows():
        lon, lat = row["lon"], row["lat"]
        if lon and lat and str(lon).strip() and str(lat).strip():
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(lon), float(lat)]
                },
                "properties": {
                    "rayon": row["rayon"],
                    "feature_count": int(row["feature_count"]),
                    "z_score": row["z_score"],
                    "classification": row["classification"],
                    "confidence": row["confidence"]
                }
            })
    
    hotspot_geojson = {"type": "FeatureCollection", "features": features}
    with open(PROCESSED_DIR / "hotspot_map.geojson", "w") as f:
        json.dump(hotspot_geojson, f, ensure_ascii=False, indent=2)
    print(f"   hotspot_map.geojson: {len(features)} features")
    
    # Create category summary per rayon for chart rendering
    matrix = pd.read_csv(PROCESSED_DIR / "rayon_feature_matrix.csv")
    cat_cols = [c for c in matrix.columns if c not in ["rayon", "total", "lon", "lat"] and c in all_categories]
    
    summary = {}
    for _, row in matrix.iterrows():
        rayon = row["rayon"]
        total = int(row["total"])
        if total > 0:
            cats = {c: int(row[c]) for c in cat_cols if row[c] > 0}
            summary[rayon] = {"total": total, "categories": cats, "lon": float(row["lon"]) if row["lon"] else None, "lat": float(row["lat"]) if row["lat"] else None}
    
    with open(PROCESSED_DIR / "rayon_summary.json", "w") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"   rayon_summary.json: {len(summary)} rayons")
    
    # Copy to public web data directory for direct access
    import shutil
    web_data = BASE / "data/processed"  
    os.makedirs(web_data, exist_ok=True)
    for fn in ["hotspot_analysis.csv", "rayon_feature_matrix.csv", "diversity_index.csv", "rayon_summary.json", "hotspot_map.geojson"]:
        src = PROCESSED_DIR / fn
        if src.exists():
            # Only copy if different path
            if src.parent != web_data:
                shutil.copy2(src, web_data / fn)
                print(f"   Copied to web data: {web_data / fn}")


# ─── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Step 1: Load all features
    features, categories = load_all_points()
    
    if not features:
        print("No features found! Run data_collection.py first.")
        sys.exit(1)
    
    # Step 2: Aggregate by rayon
    df, all_coords = aggregate_by_rayon(features)
    
    # Step 3: Spatial analysis
    hf = compute_hotspot_analysis(df, all_coords)
    
    # Step 4: Diversity analysis
    df_div = create_diversity_analysis(df)
    
    # Step 5: Category shares
    create_category_shares(df)
    
    # Step 6: Create web data files
    create_website_json_data(categories)
    
    print("\n" + "=" * 60)
    print("DATA PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Files in processed/: {len(list(PROCESSED_DIR.glob('*.csv')) + list(PROCESSED_DIR.glob('*.json')) + list(PROCESSED_DIR.glob('*.geojson')))}")
    print(f"Files in data/processed/: {len(list(PUBLIC_DATA.joinpath('processed').glob('*')))}")
