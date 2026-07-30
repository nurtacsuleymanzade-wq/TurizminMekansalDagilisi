#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP 4-6: Merge new POIs with existing data and save enhanced unified GeoJSON."""
import geopandas as gpd
import pandas as pd
import numpy as np
import json
import os
from collections import Counter
from shapely.geometry import Point

BASE_DIR = '/tmp/TurizminMekansalDagilisi'
EXISTING_GEOJSON = os.path.join(BASE_DIR, 'data/geojson/all_pois_reclassified.geojson')
TRAVEL_POIS = os.path.join(BASE_DIR, 'data/raw/azerbaijan_travel_pois.json')
MYMAPS_GEOJSON = os.path.join(BASE_DIR, 'data/geojson/google_mymaps_pois.geojson')
RAYON_BOUNDARIES = os.path.join(BASE_DIR, 'data/geojson/azerbaijan_rayon_boundaries.geojson')
OUTPUT_GEOJSON = os.path.join(BASE_DIR, 'data/geojson/all_pois_enhanced.geojson')
OUTPUT_CSV = os.path.join(BASE_DIR, 'data/processed/poi_sources.csv')
OUTPUT_CAT_COUNTS = os.path.join(BASE_DIR, 'data/processed/poi_category_counts_updated.csv')

# Standard category names matching existing data
CATEGORY_MAP = {
    'Yeme-İçme': 'Yeme-İçme',
    'Yeme-icme': 'Yeme-İçme',
    'Otel/Konaklama': 'Otel/Konaklama',
    'Tarihi-Kültürel': 'Tarihi-Kültürel',
    'Tarihi-Kulturel': 'Tarihi-Kültürel',
    'Spor': 'Spor',
    'Alışveriş-Eğlence': 'Alışveriş-Eğlence',
    'Alisveris-Eglence': 'Alışveriş-Eğlence',
    'Park-Plaj-Doğa': 'Park-Plaj-Doğa',
    'Park-Plaj-Doga': 'Park-Plaj-Doğa',
    'Dini Yerler': 'Dini Yerler',
}

def standardize_cat(cat):
    return CATEGORY_MAP.get(cat, cat)

def load_new_pois():
    """Load new POIs from both sources and merge into a single GeoDataFrame."""
    all_new = []
    
    # 1. Azerbaijan travel POIs
    if os.path.exists(TRAVEL_POIS):
        with open(TRAVEL_POIS, 'r', encoding='utf-8') as f:
            travel_pois = json.load(f)
        for p in travel_pois:
            all_new.append({
                'name': p['name'],
                'category': standardize_cat(p['category']),
                'subcategory': p.get('subcategory', ''),
                'source': p.get('source', 'azerbaijan_travel'),
                'region': p.get('region', ''),
                'rayon': p.get('rayon', ''),
                'latitude': p['latitude'],
                'longitude': p['longitude'],
                'description': p.get('description', ''),
            })
        print(f'Azerbaijan Travel POIs: {len(travel_pois)}')
    
    # 2. Google My Maps POIs
    if os.path.exists(MYMAPS_GEOJSON):
        gdf_mm = gpd.read_file(MYMAPS_GEOJSON)
        for _, row in gdf_mm.iterrows():
            lat = row.geometry.y
            lon = row.geometry.x
            all_new.append({
                'name': row.get('Name', ''),
                'category': standardize_cat(row.get('category', 'Tarihi-Kültürel')),
                'subcategory': row.get('subcategory', ''),
                'source': 'google_mymaps',
                'region': row.get('region', ''),
                'rayon': row.get('rayon', ''),
                'latitude': lat,
                'longitude': lon,
                'description': row.get('description', ''),
            })
        print(f'Google My Maps POIs: {len(gdf_mm)}')
    
    if not all_new:
        print('No new POIs found!')
        return gpd.GeoDataFrame()
    
    # Create GeoDataFrame
    gdf_new = gpd.GeoDataFrame(
        all_new,
        geometry=[Point(p['longitude'], p['latitude']) for p in all_new],
        crs='EPSG:4326'
    )
    
    # Deduplicate within new data
    before = len(gdf_new)
    gdf_new = gdf_new.drop_duplicates(subset=['name'], keep='first')
    print(f'Deduplicated new POIs: {before} -> {len(gdf_new)}')
    
    return gdf_new

def assign_rayon(gdf_new, gdf_rayons):
    """Spatial join to assign rayon to each new POI."""
    if gdf_new.empty or gdf_rayons is None:
        return gdf_new
    
    # Spatial join - point in polygon
    joined = gpd.sjoin(gdf_new, gdf_rayons[['geometry', 'adm1_name']], 
                        how='left', predicate='within')
    
    # Update rayon from boundaries where missing
    mask = (joined['rayon'].isna() | (joined['rayon'] == '') | (joined['rayon'] == 'Unknown'))
    if 'name_right' in joined.columns:
        joined.loc[mask, 'rayon'] = joined.loc[mask, 'name_right']
    
    # Drop the extra geometry column from the join
    if 'name_right' in joined.columns:
        joined = joined.drop(columns=['name_right'])
    
    # Drop index_right if present
    if 'index_right' in joined.columns:
        joined = joined.drop(columns=['index_right'])
    
    return joined

def deduplicate_with_existing(gdf_existing, gdf_new):
    """Deduplicate new POIs against existing ones by name and proximity."""
    if gdf_new.empty:
        return gdf_new
    
    existing_names = set(gdf_existing['name'].str.lower().str.strip())
    
    # Remove exact name matches
    before = len(gdf_new)
    gdf_new = gdf_new[~gdf_new['name'].str.lower().str.strip().isin(existing_names)].copy()
    print(f'Removed {before - len(gdf_new)} POIs by exact name match with existing')
    
    # Also dedup by proximity (within 0.01 degrees ~ 1km)
    if not gdf_new.empty and len(gdf_existing) > 0:
        # Use spatial index for efficiency
        sindex = gdf_existing.sindex
        to_drop = []
        for idx, row in gdf_new.iterrows():
            # Find existing POIs within 0.01 degrees
            possible_matches_idx = list(sindex.intersection(row.geometry.buffer(0.01).bounds))
            if possible_matches_idx:
                close_existing = gdf_existing.iloc[possible_matches_idx]
                distances = close_existing.distance(row.geometry)
                if (distances < 0.01).any():
                    to_drop.append(idx)
        
        if to_drop:
            gdf_new = gdf_new.drop(to_drop)
            print(f'Removed {len(to_drop)} more POIs by proximity dedup')
    
    print(f'Final new POIs after dedup: {len(gdf_new)}')
    return gdf_new

def clean_columns(gdf):
    """Ensure column names match existing schema."""
    # Rename 'name' column to match existing if needed
    col_map = {}
    if 'Name' in gdf.columns and 'name' not in gdf.columns:
        col_map['Name'] = 'name'
    if col_map:
        gdf = gdf.rename(columns=col_map)
    
    # Ensure standard columns exist
    for col in ['name', 'category', 'subcategory', 'source', 'region', 'rayon']:
        if col not in gdf.columns:
            gdf[col] = ''
    
    return gdf

def main():
    print('=== Merge and Enhance POI Data ===')
    
    # 1. Load existing data
    print()
    print('Loading existing POIs...')
    gdf_existing = gpd.read_file(EXISTING_GEOJSON)
    # Ensure CRS
    if gdf_existing.crs is None:
        gdf_existing = gdf_existing.set_crs('EPSG:4326')
    print(f'Existing POIs: {len(gdf_existing)}')
    
    # Ensure standard columns in existing
    gdf_existing = clean_columns(gdf_existing)
    
    # 2. Load new POIs
    print()
    print('Loading new POIs...')
    gdf_new = load_new_pois()
    if gdf_new.empty:
        print('No new POIs to add. Exiting.')
        return
    
    # 3. Load rayon boundaries for spatial join
    print()
    print('Loading rayon boundaries...')
    if os.path.exists(RAYON_BOUNDARIES):
        gdf_rayons = gpd.read_file(RAYON_BOUNDARIES)
        print(f'Rayon boundaries loaded: {len(gdf_rayons)}')
        # Assign rayon by spatial location
        gdf_new = assign_rayon(gdf_new, gdf_rayons)
    else:
        print('Rayon boundaries not found, skipping spatial join')
    
    # 4. Deduplicate against existing data
    print()
    print('Deduplicating...')
    gdf_new = deduplicate_with_existing(gdf_existing, gdf_new)
    
    if gdf_new.empty:
        print('No new unique POIs after deduplication.')
        gdf_merged = gdf_existing.copy()
    else:
        # 5. Clean new data columns
        gdf_new = clean_columns(gdf_new)
        
        # Ensure geometry column name is consistent
        gdf_new = gdf_new[['name', 'category', 'subcategory', 'source', 'region', 'rayon', 'geometry']]
        
        # 6. Merge
        print()
        print('Merging...')
        gdf_merged = pd.concat([gdf_existing, gdf_new], ignore_index=True)
    
    print(f'Merged POIs: {len(gdf_merged)} (existing: {len(gdf_existing)}, new: {len(gdf_new) if not gdf_new.empty else 0})')
    
    # 7. Save enhanced GeoJSON
    print()
    print('Saving enhanced GeoJSON...')
    os.makedirs(os.path.dirname(OUTPUT_GEOJSON), exist_ok=True)
    gdf_merged.to_file(OUTPUT_GEOJSON, driver='GeoJSON')
    print(f'Saved to {OUTPUT_GEOJSON}')
    print(f'File size: {os.path.getsize(OUTPUT_GEOJSON) / 1024 / 1024:.1f} MB')
    
    # 8. Generate source breakdown per rayon
    print()
    print('Generating source breakdown per rayon...')
    source_counts = gdf_merged.groupby(['rayon', 'source']).size().reset_index(name='count')
    source_counts.to_csv(OUTPUT_CSV, index=False)
    print(f'Saved to {OUTPUT_CSV}')
    
    # 9. Generate category counts
    print()
    print('Generating category counts...')
    cat_counts = gdf_merged['category'].value_counts().reset_index()
    cat_counts.columns = ['category', 'count']
    cat_counts.to_csv(OUTPUT_CAT_COUNTS, index=False)
    print(f'Saved to {OUTPUT_CAT_COUNTS}')
    
    # 10. Summary
    print()
    print('=== FINAL SUMMARY ===')
    print(f'Total POIs in enhanced dataset: {len(gdf_merged)}')
    print(f'Existing POIs: {len(gdf_existing)}')
    print(f'New POIs added: {len(gdf_new) if not gdf_new.empty else 0}')
    print()
    print('Category breakdown:')
    for cat, count in cat_counts.values:
        print(f'  {cat}: {count}')
    
    print()
    print('Source breakdown:')
    src_counts = gdf_merged['source'].value_counts()
    for src, count in src_counts.items():
        print(f'  {src}: {count}')
    
    print()
    print('Top 20 rayons by POI count:')
    rayon_counts = gdf_merged['rayon'].value_counts().head(20)
    for rayon, count in rayon_counts.items():
        print(f'  {rayon}: {count}')
    
    print()
    print('=== DONE ===')

if __name__ == '__main__':
    main()
