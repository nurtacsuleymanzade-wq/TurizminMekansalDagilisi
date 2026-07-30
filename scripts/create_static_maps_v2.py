#!/usr/bin/env python3
"""Phase 3 v2: Generate QGIS-quality static maps with enhanced 26,893 POI data.

Generates 4 NEW region maps (Naxçıvan, Qusar, Quba, Xaçmaz) + regenerates
overview and Baku maps using all_pois_enhanced.geojson.
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
pois = gpd.read_file(f"{DATA_DIR}/all_pois_enhanced.geojson")
rayons = gpd.read_file(f"{DATA_DIR}/azerbaijan_rayon_boundaries.geojson")
country = gpd.read_file(f"{DATA_DIR}/aze_admin0.geojson")

# Ensure CRS
if pois.crs is None:
    pois = pois.set_crs("EPSG:4326")
if rayons.crs is None:
    rayons = rayons.set_crs("EPSG:4326")

pois = pois.to_crs("EPSG:3857")
rayons = rayons.to_crs("EPSG:3857")
country = country.to_crs("EPSG:3857")

print(f"Total POIs: {len(pois):,}")
cats = pois['category'].value_counts()
for cat, cnt in cats.items():
    print(f"  {cat}: {cnt:,}")

# Category config (7 categories with distinct markers)
CATEGORIES = {
    "Yeme-İçme":       {"color": "#e74c3c", "marker": "o", "icon": "🍽️", "zorder": 6},
    "Otel/Konaklama":  {"color": "#3498db", "marker": "s", "icon": "🏨", "zorder": 6},
    "Tarihi-Kültürel": {"color": "#9b59b6", "marker": "^", "icon": "🏛️", "zorder": 6},
    "Spor":            {"color": "#2ecc71", "marker": "D", "icon": "⚽", "zorder": 5},
    "Alışveriş-Eğlence":{"color": "#f39c12","marker": "h", "icon": "🛍️", "zorder": 5},
    "Park-Plaj-Doğa":  {"color": "#1abc9c", "marker": "s", "icon": "🏖️", "zorder": 4},
    "Dini Yerler":     {"color": "#e67e22", "marker": "*", "icon": "🕌", "zorder": 7},
}

# Region definitions (EPSG:4326 bounds)
REGIONS = {
    "azerbaycan_genel": {
        "title": "Azerbaycan Genel — Turizm Mekansal Dağılışı",
        "bounds": None,
        "is_full": True,
        "legend_outside": True,
    },
    "baku": {
        "title": "Bakü — Turizm Mekansal Dağılışı",
        "bounds": [49.4, 40.1, 50.0, 40.6],
        "is_full": False,
        "legend_outside": True,
    },
    "naxcivan": {
        "title": "Naxçıvan — Turizm Mekansal Dağılışı",
        "bounds": [44.5, 38.8, 46.0, 39.8],
        "is_full": False,
        "legend_outside": False,
    },
    "qusar": {
        "title": "Qusar — Turizm Mekansal Dağılışı",
        "bounds": [47.8, 41.2, 48.5, 41.6],
        "is_full": False,
        "legend_outside": False,
    },
    "quba": {
        "title": "Quba — Turizm Mekansal Dağılışı",
        "bounds": [48.0, 41.0, 49.0, 41.5],
        "is_full": False,
        "legend_outside": False,
    },
    "xacmaz": {
        "title": "Xaçmaz — Turizm Mekansal Dağılışı",
        "bounds": [48.5, 41.3, 49.2, 41.8],
        "is_full": False,
        "legend_outside": False,
    },
}


def add_north_arrow(ax, x, y, size=0.02):
    """Add a north arrow to the map."""
    ax.annotate('N', xy=(x, y), xytext=(x, y - size),
                ha='center', va='center',
                fontsize=14, fontweight='bold', color='white',
                arrowprops=dict(arrowstyle='->', color='white', lw=2.5))


def add_scale_bar(ax, x, y, distance_km):
    """Add a simple scale bar."""
    dist_m = distance_km * 1000
    ax.plot([x, x + dist_m], [y, y], 'w-', lw=2.5)
    ax.plot([x, x], [y - 500, y + 500], 'w-', lw=1.5)
    ax.plot([x + dist_m, x + dist_m], [y - 500, y + 500], 'w-', lw=1.5)
    half = dist_m / 2
    ax.plot([x + half, x + half], [y - 300, y + 300], 'w-', lw=1)
    ax.text(x + dist_m/2, y + 1500, f'{distance_km} km', ha='center', va='bottom',
            fontsize=9, color='white', fontweight='bold')


def create_inset_map(ax, region_bounds_3857, country_gdf):
    """Create an inset map showing region location within Azerbaijan."""
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
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
    print(f"\n{'='*60}")
    print(f"Generating map: {region_key}")
    print(f"{'='*60}")

    figsize = (12, 16)
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.patch.set_facecolor('#0f0f1a')
    ax.set_facecolor('#0f0f1a')

    # Set bounds
    if region_info["bounds"] is not None:
        bounds_4326 = region_info["bounds"]
        bounds_3857 = box(*bounds_4326)
        bounds_3857_gdf = gpd.GeoDataFrame({'geometry': [bounds_3857]}, crs="EPSG:4326")
        bounds_3857_gdf = bounds_3857_gdf.to_crs("EPSG:3857")
        xlim = (bounds_3857_gdf.total_bounds[0], bounds_3857_gdf.total_bounds[2])
        ylim = (bounds_3857_gdf.total_bounds[1], bounds_3857_gdf.total_bounds[3])
        bbox_3857 = bounds_3857_gdf.total_bounds
    else:
        bbox_3857 = None
        xlim = (country.total_bounds[0], country.total_bounds[2])
        ylim = (country.total_bounds[1], country.total_bounds[3])

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    # Add basemap
    zoom_level = 12 if region_info["bounds"] else 8
    try:
        ctx.add_basemap(ax, crs=country.crs, source=ctx.providers.CartoDB.DarkMatter,
                       alpha=0.8, zoom=zoom_level)
        print("  Basemap: CartoDB DarkMatter")
    except Exception as e:
        print(f"  Basemap failed: {e}")
        try:
            ctx.add_basemap(ax, crs=country.crs, source=ctx.providers.OpenStreetMap.Mapnik,
                           alpha=0.5, zoom=zoom_level)
            print("  Basemap: OSM fallback")
        except Exception as e2:
            print(f"  Fallback also failed: {e2}")
            country.plot(ax=ax, color='#1a2332', edgecolor='#2d3748', linewidth=0.5)

    # Plot rayon boundaries
    try:
        rayons.plot(ax=ax, facecolor='none', edgecolor='white', linewidth=0.4, alpha=0.3)
    except:
        pass

    # Plot rayon labels for region maps
    if not region_info["is_full"] and region_info["bounds"]:
        try:
            for idx, row in rayons.iterrows():
                centroid = row.geometry.centroid
                if xlim[0] <= centroid.x <= xlim[1] and ylim[0] <= centroid.y <= ylim[1]:
                    name = row.get('adm1_name1', row.get('adm1_name', ''))
                    if name:
                        ax.text(centroid.x, centroid.y, name, fontsize=7, color='#94a3b8',
                                ha='center', va='center', alpha=0.7, style='italic',
                                fontweight='bold')
        except:
            pass

    # Filter POIs to this region
    if region_info["bounds"] is not None:
        region_pois = pois.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]
    else:
        region_pois = pois

    print(f"  POIs in view: {len(region_pois):,}")

    # Plot each category with distinct markers
    for cat_name, cat_cfg in CATEGORIES.items():
        cat_pois = region_pois[region_pois['category'] == cat_name]
        if len(cat_pois) == 0:
            continue

        marker_size = 10 if region_info["is_full"] else 18
        if cat_name == "Park-Plaj-Doğa":
            marker_size = 7 if region_info["is_full"] else 12
        elif cat_name == "Tarihi-Kültürel":
            marker_size = 12 if region_info["is_full"] else 22

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
    scale_km = 50 if region_info["is_full"] else 10
    scale_x = xlim[0] + x_range * 0.05
    scale_y = ylim[0] + y_range * 0.03
    add_scale_bar(ax, scale_x, scale_y, scale_km)

    # Add grid lines
    if region_info["is_full"]:
        glons = np.arange(44, 52, 1.0)
        glats = np.arange(38, 43, 0.5)
    else:
        glons = np.arange(44, 52, 0.5)
        glats = np.arange(38, 43, 0.25)

    for glon in glons:
        pt = gpd.GeoDataFrame({'geometry': [Point(glon, 40)]}, crs="EPSG:4326").to_crs("EPSG:3857")
        x_val = pt.geometry.x.iloc[0]
        if xlim[0] <= x_val <= xlim[1]:
            ax.axvline(x=x_val, color='#ffffff', linewidth=0.3, alpha=0.12, linestyle='--')

    for glat in glats:
        pt = gpd.GeoDataFrame({'geometry': [Point(45, glat)]}, crs="EPSG:4326").to_crs("EPSG:3857")
        y_val = pt.geometry.y.iloc[0]
        if ylim[0] <= y_val <= ylim[1]:
            ax.axhline(y=y_val, color='#ffffff', linewidth=0.3, alpha=0.12, linestyle='--')

    # Add inset map for region maps
    if region_info["bounds"] is not None and not region_info["is_full"]:
        try:
            create_inset_map(ax, bbox_3857 if bbox_3857 is not None else None, country)
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
                  markerfacecolor=cat_cfg["color"], markersize=9,
                  label=f"{cat_cfg['icon']} {cat_name} ({cat_count:,})", linewidth=0)
        )

    # Legend placement
    if region_info.get("legend_outside", True) or region_info["is_full"]:
        legend = ax.legend(handles=legend_elements, loc='upper left',
                          bbox_to_anchor=(1.02, 1), framealpha=0.9,
                          facecolor='#1a1a2e', edgecolor='#333', labelcolor='white',
                          title='POI Kategorileri', title_fontsize=11, fontsize=9,
                          handletextpad=1.5)
    else:
        legend = ax.legend(handles=legend_elements, loc='upper right',
                          framealpha=0.9, facecolor='#1a1a2e', edgecolor='#333',
                          labelcolor='white', title='POI Kategorileri',
                          title_fontsize=10, fontsize=8, handletextpad=1.5)

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
    fig.text(0.5, 0.01,
             "Kaynak: OpenStreetMap + Azərbaycan.Travel + Google My Maps | Turizmin Mekansal Dağılışı",
             ha='center', fontsize=7, color='#64748b', style='italic')

    # Save
    out_png = f"{MAPS_DIR}/{region_key}.png"
    out_pdf = f"{MAPS_DIR}/{region_key}.pdf"

    if region_info.get("legend_outside", True):
        plt.tight_layout(rect=[0, 0.02, 0.82, 1])
    else:
        plt.tight_layout(rect=[0, 0.02, 1, 1])

    fig.savefig(out_png, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"  Saved PNG: {out_png}")

    fig.savefig(out_pdf, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"  Saved PDF: {out_pdf}")

    plt.close(fig)

    size_mb = os.path.getsize(out_png) / 1024 / 1024
    print(f"  PNG size: {size_mb:.1f} MB")
    if size_mb > 10:
        print(f"  WARNING: File exceeds 10MB GitHub Pages limit!")


# Generate maps — overview + baku first, then new regions
generate_order = ["azerbaycan_genel", "baku", "naxcivan", "qusar", "quba", "xacmaz"]

for region_key in generate_order:
    if region_key in REGIONS:
        create_region_map(region_key, REGIONS[region_key])

print(f"\n{'='*60}")
print("PHASE 3 v2 COMPLETE - STATIC MAPS GENERATED")
print(f"{'='*60}")
print(f"Maps saved to: {MAPS_DIR}/")
for f in sorted(os.listdir(MAPS_DIR)):
    if f.endswith('.png') or f.endswith('.pdf'):
        size_mb = os.path.getsize(f"{MAPS_DIR}/{f}") / 1024 / 1024
        print(f"  {f}: {size_mb:.1f} MB")
