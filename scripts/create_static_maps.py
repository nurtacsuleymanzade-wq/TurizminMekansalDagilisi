#!/usr/bin/env python3
"""Phase 3: Generate QGIS-quality static maps with matplotlib+geopandas+contextily.

Generates maps for 6+ regions + overview, with all 7 POI categories.
"""
import json, os, warnings, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, box
import contextily as ctx

warnings.filterwarnings('ignore')

# Config
DATA_DIR = "data/geojson"
MAPS_DIR = "models/maps"
os.makedirs(MAPS_DIR, exist_ok=True)

# Load data
print("Loading data...")
pois = gpd.read_file(f"{DATA_DIR}/all_pois_reclassified.geojson")
rayons = gpd.read_file(f"{DATA_DIR}/azerbaijan_rayon_boundaries.geojson")
economic_regions = gpd.read_file(f"{DATA_DIR}/aze_economicregion.geojson")
country = gpd.read_file(f"{DATA_DIR}/aze_admin0.geojson")

# Ensure CRS
if pois.crs is None:
    pois = pois.set_crs("EPSG:4326")
if rayons.crs is None:
    rayons = rayons.set_crs("EPSG:4326")

pois = pois.to_crs("EPSG:3857")
rayons = rayons.to_crs("EPSG:3857")
economic_regions = economic_regions.to_crs("EPSG:3857")
country = country.to_crs("EPSG:3857")

print(f"POIs: {len(pois):,}, Rayons: {len(rayons)}, Economic regions: {len(economic_regions)}")

# Category config
CATEGORIES = {
    "Yeme-İçme": {"color": "#e74c3c", "marker": "o", "icon": "🍽️", "zorder": 6},
    "Otel/Konaklama": {"color": "#3498db", "marker": "s", "icon": "🏨", "zorder": 6},
    "Tarihi-Kültürel": {"color": "#9b59b6", "marker": "^", "icon": "🏛️", "zorder": 6},
    "Spor": {"color": "#2ecc71", "marker": "D", "icon": "⚽", "zorder": 5},
    "Alışveriş-Eğlence": {"color": "#f39c12", "marker": "o", "icon": "🛍️", "zorder": 5},
    "Park-Plaj-Doğa": {"color": "#1abc9c", "marker": "s", "icon": "🏖️", "zorder": 4},
    "Dini Yerler": {"color": "#e67e22", "marker": "*", "icon": "🕌", "zorder": 7},
}

# Define regions with bounds (in EPSG:4326, will be converted)
REGIONS = {
    "azerbaycan_genel": {
        "title": "Azerbaycan Genel Turizm POI Dağılışı",
        "bounds": None,  # Will use full country bounds
        "is_full": True
    },
    "baku": {
        "title": "Bakü ve Abşeron - Turizm POI Dağılışı",
        "bounds": [49.4, 40.1, 50.0, 40.6],  # [minx, miny, maxx, maxy] EPSG:4326
        "is_full": False
    },
    "qebele_ismayilli": {
        "title": "Qebele / İsmayıllı - Turizm POI Dağılışı",
        "bounds": [47.3, 40.5, 48.3, 41.2],
        "is_full": False
    },
    "quba_xacmaz": {
        "title": "Quba / Xaçmaz - Turizm POI Dağılışı",
        "bounds": [48.2, 41.0, 49.3, 41.8],
        "is_full": False
    },
    "lenkeran_astara": {
        "title": "Lənkəran / Astara - Turizm POI Dağılışı",
        "bounds": [48.5, 38.4, 49.0, 38.9],
        "is_full": False
    },
    "gence_goygol": {
        "title": "Gəncə / Göygöl - Turizm POI Dağılışı",
        "bounds": [46.0, 40.3, 46.6, 40.8],
        "is_full": False
    },
    "seki_oguz": {
        "title": "Şəki / Oğuz - Turizm POI Dağılışı",
        "bounds": [47.0, 40.9, 47.7, 41.4],
        "is_full": False
    },
    "samaxi_agsu": {
        "title": "Şamaxı / Ağsu - Turizm POI Dağılışı",
        "bounds": [48.0, 40.2, 49.0, 40.9],
        "is_full": False
    },
}

def add_north_arrow(ax, x, y, size=0.02):
    """Add a north arrow to the map."""
    ax.annotate('N', xy=(x, y), xytext=(x, y - size),
                ha='center', va='center',
                fontsize=14, fontweight='bold', color='white',
                arrowprops=dict(arrowstyle='->', color='white', lw=2))

def add_scale_bar(ax, x, y, distance_km, crs):
    """Add a simple scale bar."""
    # Convert km to meters in web mercator
    dist_m = distance_km * 1000
    
    # Draw scale bar
    ax.plot([x, x + dist_m], [y, y], 'w-', lw=2.5)
    ax.plot([x, x], [y - 500, y + 500], 'w-', lw=1.5)
    ax.plot([x + dist_m, x + dist_m], [y - 500, y + 500], 'w-', lw=1.5)
    
    # Draw ticks
    half = dist_m / 2
    ax.plot([x + half, x + half], [y - 300, y + 300], 'w-', lw=1)
    
    ax.text(x + dist_m/2, y + 1500, f'{distance_km} km', ha='center', va='bottom',
            fontsize=9, color='white', fontweight='bold')

def create_inset_map(ax, region_bounds_3857, country_gdf):
    """Create an inset map showing region location within Azerbaijan."""
    # Create inset axes
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    
    # Get country bounds
    country_bounds = country_gdf.total_bounds
    
    ax_inset = inset_axes(ax, width="20%", height="20%", loc="lower left",
                         bbox_to_anchor=(0.02, 0.02, 1, 1),
                         bbox_transform=ax.transAxes, borderpad=0)
    
    country_gdf.plot(ax=ax_inset, color='#1a1a2e', edgecolor='#4a5568', linewidth=0.5)
    
    if region_bounds_3857 is not None:
        region_box = box(*region_bounds_3857)
        region_gdf = gpd.GeoDataFrame({'geometry': [region_box]}, crs=country_gdf.crs)
        region_gdf.plot(ax=ax_inset, color='#e74c3c', alpha=0.5, edgecolor='#e74c3c', linewidth=1)
    
    ax_inset.set_xlim(country_bounds[0], country_bounds[2])
    ax_inset.set_ylim(country_bounds[1], country_bounds[3])
    ax_inset.axis('off')
    ax_inset.set_facecolor('#0f0f1a')

def create_region_map(region_key, region_info):
    """Generate a single region map."""
    print(f"\n=== Generating map: {region_key} ===")
    
    # Create figure with dark theme
    fig, ax = plt.subplots(1, 1, figsize=(14, 16))
    fig.patch.set_facecolor('#0f0f1a')
    ax.set_facecolor('#0f0f1a')
    
    # Set bounds
    if region_info["bounds"] is not None:
        bounds_4326 = region_info["bounds"]  # [minx, miny, maxx, maxy]
        bounds_3857 = box(*bounds_4326)
        bounds_3857 = gpd.GeoDataFrame({'geometry': [bounds_3857]}, crs="EPSG:4326")
        bounds_3857 = bounds_3857.to_crs("EPSG:3857")
        xlim = (bounds_3857.total_bounds[0], bounds_3857.total_bounds[2])
        ylim = (bounds_3857.total_bounds[1], bounds_3857.total_bounds[3])
    else:
        bounds_3857 = None
        xlim = (country.total_bounds[0], country.total_bounds[2])
        ylim = (country.total_bounds[1], country.total_bounds[3])
    
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    
    # Add basemap
    try:
        ctx.add_basemap(ax, crs=country.crs, source=ctx.providers.CartoDB.DarkMatter,
                        alpha=0.8, zoom=10 if region_info["bounds"] else 8)
        print("  Basemap: CartoDB DarkMatter")
    except Exception as e:
        print(f"  Basemap failed: {e}, trying fallback...")
        try:
            ctx.add_basemap(ax, crs=country.crs, source=ctx.providers.OpenStreetMap.Mapnik,
                            alpha=0.5, zoom=10 if region_info["bounds"] else 8)
            print("  Basemap: OSM fallback")
        except Exception as e2:
            print(f"  Fallback also failed: {e2}")
            # Draw simple land background
            country.plot(ax=ax, color='#1a2332', edgecolor='#2d3748', linewidth=0.5)
    
    # Plot rayon boundaries
    try:
        rayons.plot(ax=ax, facecolor='none', edgecolor='#4a5568', linewidth=0.4, alpha=0.7)
    except:
        pass
    
    # Plot rayon labels (for overview, skip labels to avoid clutter)
    if not region_info["is_full"]:
        try:
            # Get centroid for each rayon within view
            for idx, row in rayons.iterrows():
                centroid = row.geometry.centroid
                if xlim[0] <= centroid.x <= xlim[1] and ylim[0] <= centroid.y <= ylim[1]:
                    name = row.get('adm1_name1', row.get('adm1_name', ''))
                    if name:
                        ax.text(centroid.x, centroid.y, str(name), fontsize=5, color='#94a3b8',
                                ha='center', va='center', alpha=0.6, style='italic')
        except:
            pass
    
    # Filter POIs to this region
    if region_info["bounds"] is not None:
        region_pois = pois.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]
    else:
        region_pois = pois
    
    # Plot each category with distinct markers
    for cat_name, cat_cfg in CATEGORIES.items():
        cat_pois = region_pois[region_pois['category'] == cat_name]
        if len(cat_pois) == 0:
            continue
        
        marker_size = 12 if region_info["is_full"] else 20
        if cat_name == "Park-Plaj-Doğa":
            marker_size = 8 if region_info["is_full"] else 12
        elif cat_name == "Tarihi-Kültürel":
            marker_size = 14 if region_info["is_full"] else 24
        
        cat_pois.plot(ax=ax,
                     color=cat_cfg["color"],
                     marker=cat_cfg["marker"],
                     markersize=marker_size,
                     edgecolor='white',
                     linewidth=0.3,
                     alpha=0.8,
                     zorder=cat_cfg["zorder"],
                     label=cat_name)
    
    # Add north arrow
    y_range = ylim[1] - ylim[0]
    x_range = xlim[1] - xlim[0]
    north_x = xlim[0] + x_range * 0.08
    north_y = ylim[1] - y_range * 0.08
    add_north_arrow(ax, north_x, north_y, size=y_range * 0.03)
    
    # Add scale bar
    scale_km = 50 if region_info["is_full"] else 20
    scale_x = xlim[0] + x_range * 0.05
    scale_y = ylim[0] + y_range * 0.03
    add_scale_bar(ax, scale_x, scale_y, scale_km, country.crs)
    
    # Add grid lines
    if region_info["bounds"]:
        grid_interval = 0.3 if region_info["bounds"] else 1.0
    else:
        grid_interval = 1.0
    
    # Convert grid to 3857 for plotting
    glons = np.arange(44, 52, grid_interval if region_info["is_full"] else 0.5)
    glats = np.arange(38, 43, grid_interval if region_info["is_full"] else 0.3)
    
    for glon in glons:
        pt = gpd.GeoDataFrame({'geometry': [Point(glon, 40)]}, crs="EPSG:4326").to_crs("EPSG:3857")
        x_val = pt.geometry.x.iloc[0]
        if xlim[0] <= x_val <= xlim[1]:
            ax.axvline(x=x_val, color='#ffffff', linewidth=0.3, alpha=0.15, linestyle='--')
    
    for glat in glats:
        pt = gpd.GeoDataFrame({'geometry': [Point(45, glat)]}, crs="EPSG:4326").to_crs("EPSG:3857")
        y_val = pt.geometry.y.iloc[0]
        if ylim[0] <= y_val <= ylim[1]:
            ax.axhline(y=y_val, color='#ffffff', linewidth=0.3, alpha=0.15, linestyle='--')
    
    # Add inset map for region maps
    if region_info["bounds"] is not None and not region_info["is_full"]:
        try:
            create_inset_map(ax, bounds_3857.total_bounds if bounds_3857 is not None else None, country)
        except Exception as e:
            print(f"  Inset map skipped: {e}")
    
    # Count POIs in view
    n_pois = len(region_pois)
    
    # Create legend
    legend_elements = []
    for cat_name, cat_cfg in CATEGORIES.items():
        cat_count = len(region_pois[region_pois['category'] == cat_name])
        legend_elements.append(
            Line2D([0], [0], marker=cat_cfg["marker"], color='w',
                  markerfacecolor=cat_cfg["color"], markersize=8,
                  label=f"{cat_cfg['icon']} {cat_name} ({cat_count:,})", linewidth=0)
        )
    
    # Legend outside the map
    legend = ax.legend(handles=legend_elements, loc='upper left',
                      bbox_to_anchor=(1.02, 1), framealpha=0.9,
                      facecolor='#1a1a2e', edgecolor='#333', labelcolor='white',
                      title='POI Kategorileri', title_fontsize=11, fontsize=9,
                      handletextpad=1.5)
    
    # Title panel
    title_text = f"{region_info['title']}\nToplam {n_pois:,} POI Noktası"
    ax.set_title(title_text, fontsize=14, color='white', fontweight='bold',
                loc='center', pad=15, backgroundcolor='#1a1a2e')
    
    # Remove axis ticks
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color('#333')
        spine.set_linewidth(0.5)
    
    # Footer with source
    fig.text(0.5, 0.01, "Kaynak: OpenStreetMap (© OpenStreetMap katkıda bulunanları) | Turizmin Mekansal Dağılışı",
             ha='center', fontsize=7, color='#64748b', style='italic')
    
    # Save
    out_png = f"{MAPS_DIR}/{region_key}.png"
    out_pdf = f"{MAPS_DIR}/{region_key}.pdf"
    
    plt.tight_layout(rect=[0, 0.02, 0.85, 1])  # Leave room for legend on right
    
    fig.savefig(out_png, dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"  Saved PNG: {out_png}")
    
    fig.savefig(out_pdf, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"  Saved PDF: {out_pdf}")
    
    plt.close(fig)
    
    # Check file size
    size_mb = os.path.getsize(out_png) / 1024 / 1024
    print(f"  PNG size: {size_mb:.1f} MB")
    if size_mb > 10:
        print(f"  WARNING: File exceeds 10MB GitHub Pages limit!")

# Generate all maps
for region_key, region_info in REGIONS.items():
    create_region_map(region_key, region_info)

print("\n" + "="*60)
print("PHASE 3 COMPLETE - STATIC MAPS GENERATED")
print("="*60)
print(f"Maps saved to: {MAPS_DIR}/")
for f in sorted(os.listdir(MAPS_DIR)):
    if f.endswith('.png') or f.endswith('.pdf'):
        size_mb = os.path.getsize(f"{MAPS_DIR}/{f}") / 1024 / 1024
        print(f"  {f}: {size_mb:.1f} MB")
