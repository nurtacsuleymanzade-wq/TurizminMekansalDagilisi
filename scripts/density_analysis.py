#!/usr/bin/env python3
"""
Tourism Density Analysis for Azerbaijan
- Loads OSM POIs from multiple sources (accommodation, attractions, natural, cultural, + existing)
- Assigns weights per category
- Creates 1km x 1km grid over Azerbaijan
- Computes weighted density per cell
- Generates grid, rayon-level stats, and heatmap
"""
import os, json, warnings, sys
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_GEOJSON = os.path.join(BASE, 'data', 'geojson')
DATA_PROCESSED = os.path.join(BASE, 'data', 'processed')
MODELS_DIR = os.path.join(BASE, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Weight configuration ──────────────────────────────────────────────────
CATEGORY_WEIGHTS = {
    'accommodation': 0.35,
    'food_drink': 0.15,
    'attractions': 0.25,
    'historic': 0.10,
    'natural': 0.08,
    'cultural': 0.05,
    'transport': 0.02,
}

# ── Load all POI sources ───────────────────────────────────────────────────
def load_geojson(path):
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping")
        return gpd.GeoDataFrame()
    gdf = gpd.read_file(path)
    if len(gdf) == 0:
        return gdf
    if gdf.crs is None:
        gdf.set_crs('EPSG:4326', inplace=True)
    return gdf

print("=" * 60)
print("TOURISM DENSITY ANALYSIS — AZERBAIJAN")
print("=" * 60)

# Load existing (already classified) POIs
print("\n[1] Loading POI sources...")
existing = load_geojson(os.path.join(DATA_GEOJSON, 'all_tourism_points.geojson'))
print(f"  all_tourism_points: {len(existing)} features")

# Load OSM-specific datasets
osm_accommodation = load_geojson(os.path.join(DATA_GEOJSON, 'osm_accommodation.geojson'))
print(f"  osm_accommodation: {len(osm_accommodation)} features")

osm_attractions = load_geojson(os.path.join(DATA_GEOJSON, 'osm_attractions.geojson'))
print(f"  osm_attractions: {len(osm_attractions)} features")

osm_natural = load_geojson(os.path.join(DATA_GEOJSON, 'osm_natural.geojson'))
print(f"  osm_natural: {len(osm_natural)} features")

osm_cultural = load_geojson(os.path.join(DATA_GEOJSON, 'osm_cultural.geojson'))
print(f"  osm_cultural: {len(osm_cultural)} features")

# Existing OSM subsets (already downloaded)
osm_food_drink = load_geojson(os.path.join(DATA_GEOJSON, 'osm_food_drink.geojson'))
print(f"  osm_food_drink: {len(osm_food_drink)} features")

osm_historic = load_geojson(os.path.join(DATA_GEOJSON, 'osm_tourism_historic.geojson'))
print(f"  osm_tourism_historic: {len(osm_historic)} features")

osm_transport = load_geojson(os.path.join(DATA_GEOJSON, 'osm_transportation_hubs.geojson'))
print(f"  osm_transportation_hubs: {len(osm_transport)} features")

# ── Classify new OSM POIs into weighted categories ────────────────────────
print("\n[2] Classifying POIs into weighted categories...")

def classify_osm(gdf, default_category):
    """Add category column to OSM GeoDataFrame."""
    if len(gdf) == 0:
        return gdf
    df = gdf.copy()
    df['category'] = default_category
    return df

def classify_attractions(gdf):
    """Classify attraction POIs more specifically."""
    if len(gdf) == 0:
        return gdf
    df = gdf.copy()
    # We classify all as 'attractions' weight category
    df['category'] = 'attractions'
    return df

def classify_natural(gdf):
    """Classify natural POIs."""
    if len(gdf) == 0:
        return gdf
    df = gdf.copy()
    df['category'] = 'natural'
    return df

def classify_cultural(gdf):
    """Classify cultural POIs."""
    if len(gdf) == 0:
        return gdf
    df = gdf.copy()
    df['category'] = 'cultural'
    return df

# Classify existing POIs using their source_file/category field
def classify_existing(gdf):
    """Map existing POI categories to our weight categories."""
    if len(gdf) == 0:
        return gdf
    df = gdf.copy()
    
    # Map from existing categories
    cat_map = {
        'Otel': 'accommodation',
        'Tarihi_Anit': 'historic',
        'Diger_Tesis': 'food_drink',  # other facilities
        'Ulasim': 'transport',
        'Doga_Alani': 'natural',  # natural areas
        'Kultur_Merkezi': 'cultural',  # cultural centers
        'Turizm_Bolgesi': 'attractions',  # tourism zones
        'Destinasyon': 'attractions',  # destinations
    }
    
    if 'category' in df.columns:
        df['weight_cat'] = df['category'].map(cat_map).fillna('attractions')
    elif 'source_file' in df.columns:
        # Fallback mapping from source file name
        src_map = {
            '01_oteller': 'accommodation',
            '02_tarihi_anitlar': 'historic',
            '03_diger_tesisler': 'food_drink',
            '04_ulasim': 'transport',
            '05_doga_alanlari': 'natural',
            '06_kultur_merkezleri': 'cultural',
            '07_turizm_bolgeleri': 'attractions',
            '08_destinasyonlar': 'attractions',
        }
        df['weight_cat'] = df['source_file'].map(src_map).fillna('attractions')
    else:
        df['weight_cat'] = 'attractions'
    
    return df

existing = classify_existing(existing)
osm_accommodation = classify_osm(osm_accommodation, 'accommodation')
osm_attractions = classify_attractions(osm_attractions)
osm_natural = classify_natural(osm_natural)
osm_cultural = classify_cultural(osm_cultural)
osm_food_drink = classify_osm(osm_food_drink, 'food_drink')
osm_historic = classify_osm(osm_historic, 'historic')
osm_transport = classify_osm(osm_transport, 'transport')

# ── Combine all POIs into a single collection ─────────────────────────────
all_dfs = []
label_dfs = []

for name, gdf, cat_field in [
    ('existing', existing, 'weight_cat'),
    ('accommodation', osm_accommodation, 'category'),
    ('attractions', osm_attractions, 'category'),
    ('natural', osm_natural, 'category'),
    ('cultural', osm_cultural, 'category'),
    ('food_drink', osm_food_drink, 'category'),
    ('historic', osm_historic, 'category'),
    ('transport', osm_transport, 'category'),
]:
    if len(gdf) == 0:
        continue
    df = gdf.copy()
    if 'weight_cat' not in df.columns:
        df['weight_cat'] = df[cat_field]
    all_dfs.append(df[['geometry', 'weight_cat']])

all_pois = pd.concat(all_dfs, ignore_index=True)
all_pois = all_pois[all_pois.geometry.notna() & all_pois.geometry.is_valid]

# If there are multipoints or other geometry types, keep only points
all_pois = all_pois[all_pois.geometry.type.isin(['Point', 'MultiPoint'])]

print(f"\n  Total combined POIs: {len(all_pois)}")

# Print category breakdown
print("\n  Category breakdown:")
cat_counts = all_pois['weight_cat'].value_counts()
for cat, cnt in cat_counts.items():
    w = CATEGORY_WEIGHTS.get(cat, 0.05)
    print(f"    {cat:20s}: {cnt:4d} POIs  (weight: {w:.2f})")

# ── Compute weighted scores per POI ──────────────────────────────────────
all_pois['weight'] = all_pois['weight_cat'].map(CATEGORY_WEIGHTS).fillna(0.05)
total_weighted = all_pois['weight'].sum()
print(f"\n  Total weighted score: {total_weighted:.2f}")

# Create buffered POIs (each POI contributes its weight, effectively)
# For grid analysis, we'll just count weighted POIs per cell

# ── Load rayon boundaries ─────────────────────────────────────────────────
print("\n[3] Loading rayon boundaries...")
rayon = gpd.read_file(os.path.join(DATA_GEOJSON, 'azerbaijan_rayon_boundaries.geojson'))
print(f"  {len(rayon)} rayon boundaries loaded")

# ── Create 1km x 1km grid over Azerbaijan ─────────────────────────────────
print("\n[4] Creating 1km x 1km grid...")

# Get bounding box of Azerbaijan (slightly buffered)
bounds = rayon.total_bounds  # minx, miny, maxx, maxy
print(f"  Bounds: {bounds}")

# Create grid in a projected CRS for metric distances
# Use UTM 38N (EPSG:32638) which covers most of Azerbaijan
pois_proj = all_pois.to_crs('EPSG:32638')
rayon_proj = rayon.to_crs('EPSG:32638')

bounds_proj = rayon_proj.total_bounds
minx, miny, maxx, maxy = bounds_proj

# 1km grid
cell_size = 1000  # 1 km
x_cells = int(np.ceil((maxx - minx) / cell_size))
y_cells = int(np.ceil((maxy - miny) / cell_size))
print(f"  Grid dimensions: {x_cells} x {y_cells} = {x_cells * y_cells} cells")

# Create grid polygons
grid_cells = []
for i in range(x_cells):
    for j in range(y_cells):
        x0 = minx + i * cell_size
        y0 = miny + j * cell_size
        x1 = x0 + cell_size
        y1 = y0 + cell_size
        grid_cells.append(box(x0, y0, x1, y1))

grid_gdf = gpd.GeoDataFrame({'geometry': grid_cells}, crs='EPSG:32638')
print(f"  Created {len(grid_gdf)} grid cells")

# Clip grid to Azerbaijan boundary (keep cells intersecting rayon boundaries)
az_boundary = unary_union(rayon_proj.geometry.values)
grid_gdf = grid_gdf[grid_gdf.intersects(az_boundary)]
print(f"  After clipping to Azerbaijan: {len(grid_gdf)} cells")

# ── Spatial join: POIs to grid cells ─────────────────────────────────────
print("\n[5] Computing weighted density per grid cell...")

if len(pois_proj) > 0 and len(grid_gdf) > 0:
    # Spatial join: which POIs fall in which grid cells
    joined = gpd.sjoin(pois_proj, grid_gdf, predicate='within', how='inner')
    
    # Sum weights per grid cell
    density = joined.groupby('index_right')['weight'].sum().reset_index()
    density.columns = ['cell_idx', 'weighted_density']
    
    # Add to grid
    grid_gdf = grid_gdf.reset_index(drop=True)
    grid_gdf['cell_idx'] = grid_gdf.index
    grid_gdf = grid_gdf.merge(density, on='cell_idx', how='left')
    grid_gdf['weighted_density'] = grid_gdf['weighted_density'].fillna(0)
else:
    grid_gdf['weighted_density'] = 0

print(f"  Max density: {grid_gdf['weighted_density'].max():.2f}")
print(f"  Mean density: {grid_gdf['weighted_density'].mean():.4f}")
print(f"  Non-zero cells: {(grid_gdf['weighted_density'] > 0).sum()}")

# ── Export top 500 density cells as GeoJSON ──────────────────────────────
print("\n[6] Exporting results...")

top_500 = grid_gdf.nlargest(500, 'weighted_density').copy()
top_500_geo = top_500.to_crs('EPSG:4326')
# Keep only essential columns
top_500_geo['density'] = top_500_geo['weighted_density'].round(4)
top_500_out = top_500_geo[['geometry', 'density']]

out_grid_path = os.path.join(DATA_PROCESSED, 'density_grid.geojson')
top_500_out.to_file(out_grid_path, driver='GeoJSON')
print(f"  density_grid.geojson: {len(top_500_out)} cells")

# ── Compute density per rayon (weighted score) ───────────────────────────
print("\n[7] Computing density by rayon...")

# Spatial join: grid cells to rayons (each cell weighted by its density)
rayon_proj = rayon_proj.reset_index(drop=True)
rayon_proj['rayon_name'] = rayon_proj['adm1_name']

# Join grid cells (with density > 0) to rayons
dense_cells = grid_gdf[grid_gdf['weighted_density'] > 0].copy()
if len(dense_cells) > 0:
    cell_rayon = gpd.sjoin(dense_cells, rayon_proj, predicate='within', how='inner')
    
    # Aggregate weighted density per rayon
    rayon_density = cell_rayon.groupby('rayon_name')['weighted_density'].sum().reset_index()
    rayon_density.columns = ['rayon', 'tourism_density']
    
    # Also count POIs per rayon
    poi_counts = all_pois.to_crs('EPSG:32638')
    poi_rayon = gpd.sjoin(poi_counts, rayon_proj, predicate='within', how='inner')
    poi_rayon_counts = poi_rayon.groupby('rayon_name').size().reset_index()
    poi_rayon_counts.columns = ['rayon', 'poi_count']
    
    rayon_density = rayon_density.merge(poi_rayon_counts, on='rayon', how='left')
    rayon_density['poi_count'] = rayon_density['poi_count'].fillna(0).astype(int)
else:
    rayon_density = pd.DataFrame({'rayon': rayon_proj['rayon_name'], 'tourism_density': 0, 'poi_count': 0})

rayon_density = rayon_density.sort_values('tourism_density', ascending=False)
rayon_density.to_csv(os.path.join(DATA_PROCESSED, 'density_by_rayon.csv'), index=False)
print(f"  density_by_rayon.csv: {len(rayon_density)} rayons")
print(f"\n  Top 10 rayons by density:")
for i, row in rayon_density.head(10).iterrows():
    print(f"    {row['rayon']:25s}: {row['tourism_density']:8.2f}  ({row['poi_count']:4d} POIs)")

# ── Merge density into rayon_feature_matrix.csv ──────────────────────────
print("\n[8] Merging into rayon_feature_matrix.csv...")
feat_path = os.path.join(DATA_PROCESSED, 'rayon_feature_matrix.csv')
if os.path.exists(feat_path):
    feat_df = pd.read_csv(feat_path)
    print(f"  Original columns: {list(feat_df.columns)}")
    
    # Normalize rayon names for merging
    rayond = rayon_density[['rayon', 'tourism_density']].copy()
    
    def normalize_rayon(name):
        return name.strip().lower().replace(' ', '_').replace('-', '_').replace("'", '').replace('ə', 'e')
    
    feat_df['_norm'] = feat_df['rayon'].apply(normalize_rayon)
    rayond['_norm'] = rayond['rayon'].apply(normalize_rayon)
    
    feat_df = feat_df.merge(rayond[['_norm', 'tourism_density']], on='_norm', how='left')
    feat_df['tourism_density'] = feat_df['tourism_density'].fillna(0)
    feat_df = feat_df.drop(columns=['_norm'])
    
    feat_df.to_csv(feat_path, index=False)
    print(f"  Added 'tourism_density' column")
    print(f"  Columns now: {list(feat_df.columns)}")
else:
    print(f"  WARNING: {feat_path} not found, skipping merge")

# ── Generate matplotlib heatmap ──────────────────────────────────────────
print("\n[9] Generating density heatmap...")

fig, ax = plt.subplots(1, 1, figsize=(14, 12))

# Plot rayon boundaries
rayon_proj.boundary.plot(ax=ax, color='#334155', linewidth=0.5, alpha=0.6)

# Plot density grid cells (only non-zero)
dense_plot = grid_gdf[grid_gdf['weighted_density'] > 0].copy()
if len(dense_plot) > 0:
    # Normalize for color mapping
    vals = dense_plot['weighted_density'].values
    if vals.max() > 0:
        dense_plot['norm_density'] = vals / vals.max()
    else:
        dense_plot['norm_density'] = vals
    
    dense_plot.plot(
        ax=ax,
        column='weighted_density',
        cmap='hot',
        alpha=0.7,
        edgecolor='none',
        legend=True,
        legend_kwds={'label': 'Ağırlıklı Turizm Yoğunluğu', 'shrink': 0.6, 'pad': 0.02}
    )

# Style
ax.set_title("Azerbaycan Turizm Yoğunluk Haritası (Ağırlıklı KDE)\nOSM Turizm POI + Ağırlık Katsayıları", 
             fontsize=15, fontweight='bold', pad=15, color='#e2e8f0')
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_facecolor('#0a0e17')
fig.patch.set_facecolor('#0a0e17')
ax.tick_params(colors='#64748b')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#1e293b')
ax.spines['bottom'].set_color('#1e293b')

# Add text annotation with stats
stats_text = (
    f"Toplam POI: {len(all_pois)}\n"
    f"Işık Hücresi: {(grid_gdf['weighted_density'] > 0).sum()}\n"
    f"Maks Yoğunluk: {grid_gdf['weighted_density'].max():.2f}\n"
    f"En Yoğun Rayon: {rayon_density.iloc[0]['rayon'] if len(rayon_density) > 0 else 'N/A'}"
)
ax.text(0.02, 0.02, stats_text, transform=ax.transAxes, fontsize=10,
        color='#94a3b8', va='bottom', ha='left',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1f2e', edgecolor='#334155', alpha=0.8))

out_png = os.path.join(MODELS_DIR, 'density_heatmap.png')
plt.savefig(out_png, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.close()
print(f"  density_heatmap.png saved ({os.path.getsize(out_png)} bytes)")

# ── Summary ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("DENSITY ANALYSIS COMPLETE")
print("=" * 60)
print(f"\n  Files created:")
print(f"    {out_grid_path}")
print(f"    {os.path.join(DATA_PROCESSED, 'density_by_rayon.csv')}")
print(f"    {out_png}")
print(f"    Updated: {feat_path}")
print(f"\n  Stats:")
print(f"    Total POIs: {len(all_pois)}")
print(f"    Weighted cells: {(grid_gdf['weighted_density'] > 0).sum()}")
print(f"    Top rayon: {rayon_density.iloc[0]['rayon'] if len(rayon_density) > 0 else 'N/A'}")
print(f"    Density range: {grid_gdf['weighted_density'].min():.2f} – {grid_gdf['weighted_density'].max():.2f}")
print()
