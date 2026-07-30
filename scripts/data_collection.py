#!/usr/bin/env python3
"""
TurizminMekansalDagilisi — Data Collection Pipeline
Phase 1: Official Statistics, Boundaries, Panel Data
"""

import os, json, csv, sys
from datetime import datetime
import pandas as pd
import requests
from pathlib import Path

BASE = Path("/tmp/TurizminMekansalDagilisi")
DATA_RAW = BASE / "data" / "raw"
DATA_GEOJSON = BASE / "data" / "geojson"
DATA_PROCESSED = BASE / "data" / "processed"
METADATA = BASE / "metadata"
os.makedirs(DATA_RAW / "statistics", exist_ok=True)
os.makedirs(DATA_PROCESSED, exist_ok=True)
os.makedirs(DATA_GEOJSON, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Academic Research Bot; hermes-agent)"})

results = []

def log_result(dataset, status, details):
    results.append({"dataset": dataset, "status": status, "details": details, "timestamp": datetime.now().isoformat()})
    print(f"[{status}] {dataset}: {details}")

# ─── 1. Official Statistics: AzStat Tourism Yearbooks ───────────────────────

def try_download_azstat_tourism():
    """Try to download Tourism in Azerbaijan PDFs/Excel from stat.gov.az"""
    base_url = "https://www.stat.gov.az"
    sources = [
        {"name": "AzStat_Tourism_2025", "url": f"{base_url}/news/statistics.php?id=...", "type": "web"},
    ]
    
    # Try to scrape the statistics page for tourism sections
    try:
        r = session.get(f"{base_url}/menu/6/", timeout=15)
        if r.status_code == 200:
            log_result("AzStat_Main_Page", "FETCHED", f"Status {r.status_code}, length={len(r.text)} chars")
        else:
            log_result("AzStat_Main_Page", "FAILED", f"HTTP {r.status_code}")
    except Exception as e:
        log_result("AzStat_Main_Page", "FAILED", str(e))

    # Try direct PDF URLs (known endpoints from past years)
    pdf_urls = [
        "https://www.stat.gov.az/menu/6/statistical_yearbooks/source/tourism_2024.zip",
        "https://www.stat.gov.az/menu/6/statistical_yearbooks/tourism_2023.zip",
        "https://www.stat.gov.az/menu/6/statistical_yearbooks/source/tourism_2022.zip",
    ]
    for url in pdf_urls:
        try:
            r = session.head(url, timeout=10, allow_redirects=True)
            if r.status_code == 200:
                fname = url.split("/")[-1]
                log_result(f"AzStat_Download_{fname}", "AVAILABLE", f"Content-Type: {r.headers.get('content-type')}, Size: {r.headers.get('content-length', 'unknown')}")
            else:
                log_result(f"AzStat_Download_{url.split('/')[-1]}", "NOT_FOUND", f"HTTP {r.status_code}")
        except Exception as e:
            log_result(f"AzStat_Download_{url.split('/')[-1]}", "FAILED", str(e))


# ─── 2. Create Rayon × Year Panel Template ─────────────────────────────────

def create_panel_template():
    """Create the core rayon×year panel dataframe structure"""
    
    # Azerbaijan's 66 rayons + 11 city rayons + Nakhchivan
    rayons = [
        "Absheron", "Agdam", "Agdash", "Aghjabadi", "Agstafa", "Agsu",
        "Astara", "Babek", "Baku", "Balakan", "Barda", "Beylagan",
        "Bilasuvar", "Dashkasan", "Fuzuli", "Gadabay", "Ganja", "Goranboy",
        "Goychay", "Goygol", "Hajigabul", "Imishli", "Ismayilli", "Jabrayil",
        "Jalilabad", "Julfa", "Kalbajar", "Khachmaz", "Khizi", "Khojaly",
        "Kurdamir", "Lachin", "Lankaran", "Lerik", "Masally", "Mingachevir",
        "Naftalan", "Nakhchivan", "Neftchala", "Oghuz", "Ordubad", "Qabala",
        "Qakh", "Qazakh", "Quba", "Qubadli", "Qusar", "Saatly",
        "Sabirabad", "Salyan", "Samukh", "Shabran", "Shahbuz", "Shaki",
        "Shamakhi", "Shamkir", "Sharur", "Shirvan", "Shusha", "Siazan",
        "Sumqayit", "Tartar", "Tovuz", "Ujar", "Yardimli", "Yevlakh",
        "Zangilan", "Zaqatala", "Zardab"
    ]
    
    years = [2005, 2010, 2015, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    
    # Create panel
    panel_rows = []
    for rayon in rayons:
        for year in years:
            panel_rows.append({
                "rayon_id": rayon.lower().replace(" ", "_"),
                "rayon_name": rayon,
                "year": year,
                "facilities": None,     # Otel ve benzeri konaklama tesisi sayısı
                "rooms": None,           # Oda sayısı
                "beds": None,            # Yatak kapasitesi
                "total_guests": None,    # Konaklayan toplam kişi
                "domestic_tourists": None,  # Yerli turist sayısı
                "foreign_tourists": None,   # Yabancı turist sayısı
                "total_nights": None,    # Toplam geceleme
                "domestic_nights": None, # Yerli geceleme
                "foreign_nights": None,  # Yabancı geceleme
                "occupancy_rate": None,  # Doluluk oranı (%)
                "avg_stay": None,        # Ortalama kalış süresi (gün)
                "revenue_azn": None,     # Otel gelirleri (AZN)
                "employees": None,        # Çalışan sayısı
                "travel_agencies": None,  # Seyahat acentesi sayısı
                "population": None,      # Nüfus
                "area_km2": None,        # Yüzölçümü (km²)
            })
    
    df = pd.DataFrame(panel_rows)
    df.to_csv(DATA_PROCESSED / "rayon_year_panel.csv", index=False)
    log_result("Rayon_Year_Panel", "CREATED", f"{len(df)} rows ({len(rayons)} rayons × {len(years)} years)")
    
    # Also create a simplified version with just key indicators
    summary = df[["rayon_id", "rayon_name", "year", "population", "area_km2",
                  "facilities", "beds", "total_guests", "total_nights",
                  "domestic_tourists", "foreign_tourists"]].copy()
    summary.to_csv(DATA_PROCESSED / "tourism_panel_key_indicators.csv", index=False)
    
    return df

# ─── 3. Copy existing GeoJSON data into repo ────────────────────────────────

def copy_existing_geojson():
    """Copy existing tourism point data into the repo structure"""
    source_dir = Path("/root/az_tourism_data")
    if not source_dir.exists():
        log_result("Copy_GeoJSON", "SKIPPED", "Source dir /root/az_tourism_data not found")
        return
    
    count = 0
    for f in sorted(source_dir.glob("*.geojson")):
        target = DATA_GEOJSON / f.name
        data = json.loads(f.read_text())
        features = len(data.get("features", []))
        
        # Copy to repo
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        count += 1
        
        # Analyze categories
        cats = {}
        for feat in data.get("features", []):
            cat = feat.get("properties", {}).get("category", "unknown")
            cats[cat] = cats.get(cat, 0) + 1
        
        log_result(f"Copy_{f.name}", "COPIED", f"{features} features, categories: {cats}")
    
    if count == 0:
        log_result("Copy_GeoJSON", "SKIPPED", "No GeoJSON files found")
    
    return count

# ─── 4. Create Source Registry Update ─────────────────────────────────────

def update_source_registry():
    """Update source_registry.csv with actual processing status"""
    reg_path = METADATA / "source_registry.csv"
    if not reg_path.exists():
        log_result("Source_Registry", "SKIPPED", "File not found")
        return
    
    df = pd.read_csv(reg_path)
    
    # Mark existing data sources
    for idx, row in df.iterrows():
        ds_name = row["dataset_name"]
        
        # Check if GeoJSON data exists for OSM sources
        if "OSM" in ds_name:
            geojson_file = DATA_GEOJSON / f"osm_{ds_name.lower()}.geojson"
            if geojson_file.exists():
                df.at[idx, "processing_status"] = "DOWNLOADED"
                df.at[idx, "download_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Check for copied tourism data
        if ds_name == "AzStat_Tourism_Yearbook":
            df.at[idx, "processing_status"] = "PARTIALLY_COLLECTED"
            df.at[idx, "download_date"] = datetime.now().strftime("%Y-%m-%d")
            df.at[idx, "notes"] = "Template created. PDF download from stat.gov.az pending."
    
    df.to_csv(reg_path, index=False)
    log_result("Source_Registry", "UPDATED", f"{len(df)} entries")

# ─── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("TURİZMİN MEKANSAL DAĞILIŞI — Data Collection Pipeline")
    print("=" * 60)
    
    # Step 1: Try AzStat downloads
    print("\n--- Step 1: AzStat Tourism Statistics ---")
    try_download_azstat_tourism()
    
    # Step 2: Create panel template
    print("\n--- Step 2: Rayon × Year Panel ---")
    create_panel_template()
    
    # Step 3: Copy existing data
    print("\n--- Step 3: Copy Existing GeoJSON ---")
    copy_existing_geojson()
    
    # Step 4: Update registry
    print("\n--- Step 4: Update Source Registry ---")
    update_source_registry()
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"  [{r['status']:>8}] {r['dataset']}: {r['details']}")
    
    print(f"\nTotal operations: {len(results)}")
    print(f"Pipeline complete.")
