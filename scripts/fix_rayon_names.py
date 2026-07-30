#!/usr/bin/env python3
"""Fix rayon name mapping in density_by_rayon.csv and merge into feature matrix."""
import pandas as pd
import geopandas as gpd
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PROCESSED = os.path.join(BASE, 'data', 'processed')
DATA_GEOJSON = os.path.join(BASE, 'data', 'geojson')

# Load boundary names
rayon = gpd.read_file(os.path.join(DATA_GEOJSON, 'azerbaijan_rayon_boundaries.geojson'))

# Load the density_by_rayon.csv (produced by density_analysis.py)
density_path = os.path.join(DATA_PROCESSED, 'density_by_rayon.csv')
density_df = pd.read_csv(density_path)

# Build mapping from boundary name -> CSV rayon name
# The CSV uses Turkish/Azeri style transliterations
boundary_to_csv = {
    'Absheron': 'Absheron', 'Agdash': 'Agdash', 'Agdjabadi': 'Aghjabadi',
    'Aghdam': 'Agdam', 'Aghstafa': 'Agstafa', 'Aghsu': 'Agsu',
    'Astara': 'Astara', 'Babek': 'Babek', 'Baku': 'Baku',
    'Balakan': 'Balakan', 'Barda': 'Barda', 'Beylagan': 'Beylagan',
    'Bilasuvar': 'Bilasuvar', 'Dashkasan': 'Dashkasan', 'Fuzuli': 'Fuzuli',
    'Gabala': 'Qabala', 'Gadabay': 'Gadabay', 'Gakh': 'Qakh',
    'Ganja': 'Ganja', 'Gazakh': 'Qazakh', 'Gobustan': 'Gobustan',
    'Goranboy': 'Goranboy', 'Goychay': 'Goychay', 'Goygol': 'Goygol',
    'Guba': 'Quba', 'Gubadly': 'Qubadli', 'Gusar': 'Qusar',
    'Hajigabul': 'Hajigabul', 'Imishly': 'Imishli', 'Ismayilly': 'Ismayilli',
    'Jabrayil': 'Jabrayil', 'Jalilabad': 'Jalilabad', 'Julfa': 'Julfa',
    'Kalbajar': 'Kalbajar', 'Kengerli': 'Kangarli',
    'Khachmaz': 'Khachmaz', 'Khankendi': 'Khankendi',
    'Khizy': 'Khizi', 'Khojaly': 'Khojaly', 'Khojavand': 'Khojavand',
    'Kurdamir': 'Kurdamir', 'Lachin': 'Lachin', 'Lankaran': 'Lankaran',
    'Lerik': 'Lerik', 'Masally': 'Masally', 'Mingechevir': 'Mingachevir',
    'Naftalan': 'Naftalan', 'Nakhchivan': 'Nakhchivan',
    'Neftchala': 'Neftchala', 'Oghuz': 'Oghuz', 'Ordubad': 'Ordubad',
    'Saatly': 'Saatly', 'Sabirabad': 'Sabirabad', 'Sadarak': 'Sedarak',
    'Salyan': 'Salyan', 'Samukh': 'Samukh', 'Shabran': 'Shabran',
    'Shahbuz': 'Shahbuz', 'Shaki': 'Shaki', 'Shamakhy': 'Shamakhi',
    'Shamkir': 'Shamkir', 'Sharur': 'Sharur', 'Shirvan': 'Shirvan',
    'Shusha': 'Shusha', 'Siyazan': 'Siazan', 'Sumgait': 'Sumqayit',
    'Tartar': 'Tartar', 'Tovuz': 'Tovuz', 'Ujar': 'Ujar',
    'Yardimly': 'Yardimli', 'Yevlakh': 'Yevlakh',
    'Zagatala': 'Zaqatala', 'Zangilan': 'Zangilan', 'Zardab': 'Zardab',
}

# Map boundary names to CSV names
density_df['rayon'] = density_df['rayon'].map(boundary_to_csv).fillna(density_df['rayon'])

# Save updated density_by_rayon.csv
density_df.to_csv(density_path, index=False)
print(f"Updated density_by_rayon.csv with {len(density_df)} rayons")
print(f"\nTop 10:")
for _, row in density_df.head(10).iterrows():
    print(f"  {row['rayon']:20s}: {row['tourism_density']:8.2f}  ({row['poi_count']:4d} POIs)")

# ── Merge into rayon_feature_matrix.csv ──────────────────────────────────
feat_path = os.path.join(DATA_PROCESSED, 'rayon_feature_matrix.csv')
feat_df = pd.read_csv(feat_path)
print(f"\nFeature matrix: {feat_df.shape}")

# Remove old tourism_density if exists
if 'tourism_density' in feat_df.columns:
    feat_df = feat_df.drop(columns=['tourism_density'])

# Merge
feat_df = feat_df.merge(density_df[['rayon', 'tourism_density']], on='rayon', how='left')
feat_df['tourism_density'] = feat_df['tourism_density'].fillna(0)
feat_df.to_csv(feat_path, index=False)
print(f"Merged. Columns: {list(feat_df.columns)}")
print(f"Non-zero density rows: {(feat_df['tourism_density'] > 0).sum()}/{len(feat_df)}")
print("Done!")
