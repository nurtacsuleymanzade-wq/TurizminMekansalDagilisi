#!/usr/bin/env python3
"""
Tourist Brochure Map Generator — Turistik Broşür Stili Haritalar
Creates light-filled, pastel-colored, icon-rich, bilingual tourist maps
matching the style of official Azerbaijani tourism maps.
"""

import json, os, warnings, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.font_manager as fm
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, box, Polygon, LineString
import contextily as ctx

warnings.filterwarnings('ignore')

# ── Config ──────────────────────────────────────────────────
DATA_DIR = "data/geojson"
MAPS_DIR = "models/maps/tourist"
os.makedirs(MAPS_DIR, exist_ok=True)

# Load data
pois = gpd.read_file(f"{DATA_DIR}/all_pois_enhanced.geojson")
rayons = gpd.read_file(f"{DATA_DIR}/azerbaijan_rayon_boundaries.geojson")
country = gpd.read_file(f"{DATA_DIR}/aze_admin0.geojson")

if pois.crs is None:
    pois = pois.set_crs("EPSG:4326")
if rayons.crs is None:
    rayons = rayons.set_crs("EPSG:4326")

pois = pois.to_crs("EPSG:3857")
rayons = rayons.to_crs("EPSG:3857")
country = country.to_crs("EPSG:3857")

# ── TOURIST COLOR PALETTE ────────────────────────────────────
# Light pastels for regions, matching the official tourism map style
BG_CREAM    = '#f5f0e8'    # Map background
BG_LIGHTER  = '#faf7f0'    # Outer background
REGION_COLORS = ['#e8f4e8', '#f5f0d0', '#e8e0f0', '#f0e8d8',
                 '#d8f0e8', '#f5e8e0', '#e0f0f0', '#f0f0d8',
                 '#e0e8f5', '#f5e0e0', '#d0f0d0', '#f0d8f0',
                 '#e8f0d8', '#f5f0e0']

# Category colors — vibrant for tourist map
CATEGORIES = {
    "Yeme-İçme":       {"color": "#e74c3c", "icon": "🍽", "label": "Restoran/Kafe"},
    "Otel/Konaklama":  {"color": "#8e44ad", "icon": "🏨", "label": "Otel/Hotel"},
    "Tarihi-Kültürel": {"color": "#2980b9", "icon": "🏛", "label": "Muzey"},
    "Spor":            {"color": "#27ae60", "icon": "⚽", "label": "Spor"},
    "Alışveriş-Eğlence":{"color": "#e67e22","icon": "🛍", "label": "Alışveriş"},
    "Park-Plaj-Doğa":  {"color": "#16a085", "icon": "🌳", "label": "Park"},
    "Dini Yerler":     {"color": "#c0392b", "icon": "🕌", "label": "Dini Yer"},
}

# ── REGION DEFINITIONS ──────────────────────────────────────
REGIONS = {
    "quba_tourist": {
        "title_az": "QUBA ŞƏHƏRİ",
        "title_en": "GUBA CITY — TOURIST MAP",
        "subtitle": "Quba Regional Turizm İdarəsi",
        "bounds": [48.44, 41.32, 48.56, 41.40],
        "zoom": 14,
        "info_box": True,
    },
    "quba_qusar_region": {
        "title_az": "QUBA-QUSAR RAYONU",
        "title_en": "GUBA-GUSAR REGION MAP",
        "subtitle": "Şahdağ Milli Parkı • Afurca Şəlaləsi • Xınalıq",
        "bounds": [47.8, 40.8, 48.8, 41.7],
        "zoom": 11,
        "info_box": True,
    },
    "naxcivan_tourist": {
        "title_az": "NAXÇIVAN MUXTAR RESPUBLİKASI",
        "title_en": "NAKHCHIVAN AUTONOMOUS REPUBLIC — TOURIST MAP",
        "subtitle": "Tarixi İpək Yolu Üzərində",
        "bounds": [44.5, 38.8, 46.2, 39.9],
        "zoom": 10,
        "info_box": True,
    },
    "qebele_tourist": {
        "title_az": "QƏBƏLƏ RAYONU",
        "title_en": "GABALA REGION — TOURIST MAP",
        "subtitle": "Qafqazın İncisi • Tufandağ • Nohur Gölü",
        "bounds": [47.5, 40.7, 48.2, 41.2],
        "zoom": 12,
        "info_box": True,
    },
    "baku_tourist": {
        "title_az": "BAKI ŞƏHƏRİ",
        "title_en": "BAKU CITY — TOURIST MAP",
        "subtitle": "Azərbaycanın Paytaxtı • İçərişəhər • Bulvar",
        "bounds": [49.4, 40.1, 50.1, 40.6],
        "zoom": 12,
        "info_box": True,
    },
    "xacmaz_tourist": {
        "title_az": "XAÇMAZ RAYONU",
        "title_en": "KHACHMAZ REGION — TOURIST MAP",
        "subtitle": "Xəzər Sahili • Nabran • Meşəliklər",
        "bounds": [48.5, 41.3, 49.2, 41.8],
        "zoom": 12,
        "info_box": True,
    },
    "azerbaycan_tourist": {
        "title_az": "AZƏRBAYCAN RESPUBLİKASI",
        "title_en": "REPUBLIC OF AZERBAIJAN — TOURIST MAP",
        "subtitle": "Odlar Yurdu • Qafqazın İncisi",
        "bounds": None,
        "zoom": 8,
        "info_box": False,
    },
    "lankaran_tourist": {
        "title_az": "LƏNKƏRAN RAYONU",
        "title_en": "LANKARAN REGION — TOURIST MAP",
        "subtitle": "Xəzər Sahili • Talış Dağları • İstisu",
        "bounds": [48.5, 38.5, 49.1, 39.0],
        "zoom": 12,
        "info_box": True,
    },
    "sheki_tourist": {
        "title_az": "ŞƏKİ RAYONU",
        "title_en": "SHEKI REGION — TOURIST MAP",
        "subtitle": "İpək Yolu • Xan Sarayı • Kiş Alban Məbədi",
        "bounds": [47.0, 40.9, 47.5, 41.4],
        "zoom": 12,
        "info_box": True,
    },
    "gence_tourist": {
        "title_az": "GƏNCƏ ŞƏHƏRİ",
        "title_en": "GANJA CITY — TOURIST MAP",
        "subtitle": "Qədim Azərbaycan Şəhəri • Göygöl • Nizami",
        "bounds": [46.1, 40.5, 46.5, 40.8],
        "zoom": 13,
        "info_box": True,
    },
}

# ── HELPER FUNCTIONS ────────────────────────────────────────

def add_north_arrow_light(ax, x, y, size=0.02):
    """Light-style north arrow for tourist maps."""
    ax.annotate('N', xy=(x, y), xytext=(x, y - size),
                ha='center', va='center',
                fontsize=14, fontweight='bold', color='#333333',
                arrowprops=dict(arrowstyle='->', color='#333333', lw=2.5))


def add_scale_bar_light(ax, x, y, distance_km, crs_epsg=3857):
    """Add a light-style scale bar."""
    import matplotlib.transforms as transforms

    # Convert km to meters in projected CRS
    dist_m = distance_km * 1000

    # Draw scale bar
    bar_y = y
    ax.plot([x, x + dist_m], [bar_y, bar_y], '-', color='#333333', lw=3)

    # Tick marks
    ax.plot([x, x], [bar_y - 400, bar_y + 400], '-', color='#333333', lw=1.5)
    ax.plot([x + dist_m, x + dist_m], [bar_y - 400, bar_y + 400], '-', color='#333333', lw=1.5)
    
    # Halfway tick
    half = dist_m / 2
    ax.plot([x + half, x + half], [bar_y - 250, bar_y + 250], '-', color='#333333', lw=1.0)

    # Label
    ax.text(x + dist_m / 2, bar_y + 1800, f'{distance_km} km',
            ha='center', va='bottom', fontsize=9, color='#333333',
            fontweight='bold', fontfamily='sans-serif')


def add_location_inset(ax, region_bounds_3857, country_gdf):
    """Add inset map showing region location in Azerbaijan."""
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes

    ax_inset = inset_axes(ax, width="22%", height="22%", loc="lower left",
                         bbox_to_anchor=(0.01, 0.01, 1, 1),
                         bbox_transform=ax.transAxes, borderpad=0)

    country_gdf.plot(ax=ax_inset, color='#e8e0d0', edgecolor='#999999', linewidth=0.5)

    if region_bounds_3857 is not None:
        region_box = box(*region_bounds_3857)
        region_gdf = gpd.GeoDataFrame({'geometry': [region_box]}, crs=country_gdf.crs)
        region_gdf.plot(ax=ax_inset, color='#e74c3c', alpha=0.4, edgecolor='#c0392b', linewidth=1.5)

    bounds = country_gdf.total_bounds
    ax_inset.set_xlim(bounds[0], bounds[2])
    ax_inset.set_ylim(bounds[1], bounds[3])
    ax_inset.axis('off')
    ax_inset.set_facecolor('#f5f0e8')


def add_info_box(ax, region_key, region_pois):
    """Add an information box with POI summary and contact info."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Position info box at bottom-left
    box_x = xlim[0] + (xlim[1] - xlim[0]) * 0.02
    box_y = ylim[0] + (ylim[1] - ylim[0]) * 0.02
    box_w = (xlim[1] - xlim[0]) * 0.25
    box_h = (ylim[1] - ylim[0]) * 0.32

    rect = FancyBboxPatch((box_x, box_y), box_w, box_h,
                          boxstyle="round,pad=0.02",
                          facecolor='white', edgecolor='#cccccc',
                          linewidth=1.5, alpha=0.92, zorder=100)
    ax.add_patch(rect)

    # Count POIs by category
    cat_counts = {}
    for cat in CATEGORIES:
        cnt = len(region_pois[region_pois['category'] == cat])
        if cnt > 0:
            cat_counts[cat] = cnt

    # Write info
    texts = []
    texts.append(("INFO", 12, True, '#2980b9'))
    texts.append((f"Toplam POI: {len(region_pois):,}", 8, False, '#333333'))
    texts.append(("─" * 20, 7, False, '#cccccc'))

    for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        cfg = CATEGORIES[cat]
        texts.append((f"{cfg['icon']} {cfg['label']}: {count:,}", 7, False, '#555555'))

    texts.append(("─" * 20, 7, False, '#cccccc'))
    texts.append(("© Turizmin Mekansal Dağılışı", 6, False, '#999999'))
    texts.append(("N.T.Süleymanzadə | AzTU 2026", 6, False, '#999999'))

    y_offset = box_y + box_h - 5000
    for text, size, bold, color in texts:
        ax.text(box_x + box_w * 0.05, y_offset, text,
                fontsize=size, color=color, fontweight='bold' if bold else 'normal',
                zorder=101, fontfamily='sans-serif')
        y_offset -= box_h / (len(texts) + 3)


def add_title_panel(ax, region_info):
    """Add an attractive title panel at the top."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Title background bar
    title_h = (ylim[1] - ylim[0]) * 0.12
    title_rect = FancyBboxPatch((xlim[0], ylim[1] - title_h),
                                xlim[1] - xlim[0], title_h,
                                boxstyle="round,pad=0.01",
                                facecolor='#1a5276', edgecolor='#1a5276',
                                linewidth=2, alpha=0.92, zorder=90)
    ax.add_patch(title_rect)

    # Title text — Azerbaijani (main)
    ax.text((xlim[0] + xlim[1]) / 2, ylim[1] - title_h * 0.65,
            region_info['title_az'],
            fontsize=13, color='white', fontweight='bold',
            ha='center', va='center', zorder=91)

    # English subtitle
    ax.text((xlim[0] + xlim[1]) / 2, ylim[1] - title_h * 0.3,
            region_info['title_en'],
            fontsize=9, color='#bdc3c7', fontweight='normal',
            ha='center', va='center', zorder=91, style='italic')

    # Tagline
    if 'subtitle' in region_info:
        ax.text((xlim[0] + xlim[1]) / 2, ylim[1] - title_h * 0.08,
                region_info['subtitle'],
                fontsize=7, color='#95a5a6',
                ha='center', va='bottom', zorder=91)


def add_legend_panel(ax, region_pois):
    """Add a clean legend panel."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()

    # Position at bottom-right
    box_x = xlim[1] - (xlim[1] - xlim[0]) * 0.22
    box_y = ylim[0] + (ylim[1] - ylim[0]) * 0.02
    box_w = (xlim[1] - xlim[0]) * 0.20
    box_h = (ylim[1] - ylim[0]) * 0.30

    rect = FancyBboxPatch((box_x, box_y), box_w, box_h,
                          boxstyle="round,pad=0.02",
                          facecolor='white', edgecolor='#cccccc',
                          linewidth=1.5, alpha=0.95, zorder=100)
    ax.add_patch(rect)

    # Legend header
    y_pos = box_y + box_h - 4000
    ax.text(box_x + box_w * 0.55, y_pos, "ŞƏRTİ İŞARƏLƏR",
            fontsize=9, color='#1a5276', fontweight='bold',
            ha='center', zorder=101)
    ax.text(box_x + box_w * 0.55, y_pos - 3000, "Conventional Signs",
            fontsize=7, color='#7f8c8d', ha='center', zorder=101)

    y_pos -= 6000

    for cat_name, cfg in CATEGORIES.items():
        cnt = len(region_pois[region_pois['category'] == cat_name])
        if cnt == 0:
            continue

        # Colored circle
        circle = mpatches.Circle((box_x + box_w * 0.12, y_pos), 1500,
                                 color=cfg['color'], zorder=101,
                                 alpha=0.85)
        ax.add_patch(circle)

        # Label
        lbl = f"{cfg['icon']} {cfg['label']} ({cnt:,})"
        ax.text(box_x + box_w * 0.25, y_pos, lbl,
                fontsize=6.5, color='#333333', zorder=101, va='center',
                fontfamily='sans-serif')

        y_pos -= 4200


def add_border_frame(ax):
    """Add a decorative border frame around the map."""
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color('#999999')
        spine.set_linewidth(2.0)


# ── MAIN MAP FUNCTION ────────────────────────────────────────

def create_tourist_map(region_key, region_info):
    """Generate a single tourist-style map."""
    print(f"\n{'='*60}")
    print(f"Tourist Map: {region_key}")
    print(f"  {region_info['title_az']}")
    print(f"  {region_info['title_en']}")
    print(f"{'='*60}")

    # Create figure with appropriate aspect ratio
    if region_info['bounds'] is None:
        figsize = (16, 12)
    else:
        b = region_info['bounds']
        aspect = (b[2] - b[0]) / (b[3] - b[1])
        figsize = (14, 10 / aspect) if aspect < 1.5 else (16, 12 / aspect)

    fig, ax = plt.subplots(1, 1, figsize=figsize)
    fig.patch.set_facecolor(BG_LIGHTER)
    ax.set_facecolor(BG_CREAM)

    # Set bounds
    if region_info['bounds'] is not None:
        bounds_4326 = region_info['bounds']
        bounds_3857_gdf = gpd.GeoDataFrame(
            {'geometry': [box(*bounds_4326)]}, crs="EPSG:4326"
        ).to_crs("EPSG:3857")
        bbox = bounds_3857_gdf.total_bounds
        xlim = (bbox[0], bbox[2])
        ylim = (bbox[1], bbox[3])
    else:
        bbox = country.total_bounds
        xlim = (bbox[0], bbox[2])
        ylim = (bbox[1], bbox[3])

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    # ── Basemap: LIGHT style! ─────────────────────────────~
    zoom = region_info.get('zoom', 10)
    try:
        ctx.add_basemap(ax, crs=country.crs,
                       source=ctx.providers.CartoDB.Positron,
                       alpha=0.7, zoom=zoom)
        print("  Basemap: CartoDB Positron (light)")
    except Exception:
        try:
            ctx.add_basemap(ax, crs=country.crs,
                           source=ctx.providers.CartoDB.PositronNoLabels,
                           alpha=0.8, zoom=zoom)
            print("  Basemap: PositronNoLabels")
        except Exception:
            try:
                ctx.add_basemap(ax, crs=country.crs,
                               source=ctx.providers.OpenStreetMap.Mapnik,
                               alpha=0.5, zoom=zoom)
                print("  Basemap: OSM (fallback)")
            except Exception as e:
                print(f"  No basemap: {e}")
                country.plot(ax=ax, color='#e8e0d0', edgecolor='#cccccc', linewidth=0.5)

    # ── Rayon boundaries with pastel colors ──────────────────
    try:
        rayons.plot(ax=ax, facecolor='none', edgecolor='#aaaaaa',
                   linewidth=0.6, alpha=0.6, linestyle='-')
        print("  Rayon boundaries drawn")
    except Exception as e:
        print(f"  Rayon boundaries failed: {e}")

    # ── Region pastel fill ───────────────────────────────────
    if region_info['bounds'] is not None:
        try:
            # Find rayons in view and color them
            region_rayons = rayons.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]
            for i, (idx, row) in enumerate(region_rayons.iterrows()):
                color = REGION_COLORS[i % len(REGION_COLORS)]
                p = row.geometry
                if p is not None:
                    gpd.GeoSeries([p]).plot(ax=ax, color=color, alpha=0.5,
                                            edgecolor='#999999', linewidth=0.5)
            
            # Labels
            for idx, row in region_rayons.iterrows():
                centroid = row.geometry.centroid
                name = row.get('adm1_name1', row.get('adm1_name', ''))
                if name and xlim[0] <= centroid.x <= xlim[1] and ylim[0] <= centroid.y <= ylim[1]:
                    ax.text(centroid.x, centroid.y, name,
                           fontsize=7, color='#666666', ha='center',
                           va='center', alpha=0.8, fontweight='bold',
                           style='italic')
            print(f"  Region fill: {len(region_rayons)} rayons")
        except Exception as e:
            print(f"  Region fill failed: {e}")

    # ── Filter POIs to this region ───────────────────────────
    if region_info['bounds'] is not None:
        region_pois = pois.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]
    else:
        region_pois = pois

    print(f"  POIs in view: {len(region_pois):,}")

    # ── Plot each category with colorful markers ──────────────
    for cat_name, cfg in CATEGORIES.items():
        cat_pois = region_pois[region_pois['category'] == cat_name]
        if len(cat_pois) == 0:
            continue

        # Larger markers for tourist maps
        if region_info['bounds'] is None:
            ms = 8
        else:
            ms = 14

        cat_pois.plot(ax=ax,
                     color=cfg['color'],
                     marker='o',
                     markersize=ms,
                     edgecolor='white',
                     linewidth=0.5,
                     alpha=0.85,
                     zorder=8,
                     label=cfg['label'])

    # ── Map decorations ──────────────────────────────────────
    y_range = ylim[1] - ylim[0]
    x_range = xlim[1] - xlim[0]

    # North arrow
    add_north_arrow_light(ax, xlim[0] + x_range * 0.92,
                          ylim[1] - y_range * 0.10, size=y_range * 0.03)

    # Scale bar
    if region_info['bounds'] is None:
        scale_km = 50
    elif x_range < 20000:
        scale_km = 2
    elif x_range < 50000:
        scale_km = 5
    elif x_range < 100000:
        scale_km = 10
    else:
        scale_km = 20

    add_scale_bar_light(ax, xlim[0] + x_range * 0.05,
                        ylim[0] + y_range * 0.04, scale_km)

    # ── Title panel (blue banner) ────────────────────────────
    add_title_panel(ax, region_info)

    # ── Legend panel ─────────────────────────────────────────
    add_legend_panel(ax, region_pois)

    # ── Info box ─────────────────────────────────────────────
    if region_info.get('info_box', False):
        add_info_box(ax, region_key, region_pois)

    # ── Inset map ────────────────────────────────────────────
    if region_info['bounds'] is not None:
        try:
            from mpl_toolkits.axes_grid1.inset_locator import inset_axes
            ax_inset = inset_axes(ax, width="22%", height="22%", loc="lower left",
                                 bbox_to_anchor=(0.01, 0.01, 1, 1),
                                 bbox_transform=ax.transAxes, borderpad=0)
            country.plot(ax=ax_inset, color='#e8e0d0',
                        edgecolor='#999999', linewidth=0.5)
            region_box = gpd.GeoDataFrame(
                {'geometry': [box(*region_info['bounds'])]}, crs="EPSG:4326"
            ).to_crs(country.crs)
            region_box.plot(ax=ax_inset, color='#e74c3c', alpha=0.4,
                           edgecolor='#c0392b', linewidth=1.5)
            ctry_bounds = country.total_bounds
            ax_inset.set_xlim(ctry_bounds[0], ctry_bounds[2])
            ax_inset.set_ylim(ctry_bounds[1], ctry_bounds[3])
            ax_inset.axis('off')
            ax_inset.set_facecolor(BG_CREAM)
            print("  Inset map added")
        except Exception as e:
            print(f"  Inset map skipped: {e}")

    # ── Frame ────────────────────────────────────────────────
    add_border_frame(ax)

    # ── Remove axis ticks ─────────────────────────────────────
    ax.set_xticks([])
    ax.set_yticks([])

    # ── Footer ───────────────────────────────────────────────
    fig.text(0.5, 0.010,
             "Məlumat mənbəyi: OpenStreetMap, Azərbaycan Respublikası Dövlət Statistika Komitəsi | © Turizmin Mekansal Dağılışı — N.T.Süleymanzadə, AzTU 2026",
             ha='center', fontsize=6, color='#999999', style='italic')

    # ── Save ──────────────────────────────────────────────────
    out_png = f"{MAPS_DIR}/{region_key}.png"
    fig.savefig(out_png, dpi=300, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    
    size_mb = os.path.getsize(out_png) / (1024 * 1024)
    print(f"  ✓ Saved: {out_png} ({size_mb:.1f} MB)")
    plt.close(fig)
    return out_png


# ── GENERATE ALL ─────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("TOURIST BROCHURE MAP GENERATOR")
    print("Turistik Broşür Stili Harita Üretici")
    print("=" * 60)

    for region_key, region_info in REGIONS.items():
        create_tourist_map(region_key, region_info)

    print(f"\n{'='*60}")
    print("ALL TOURIST MAPS GENERATED!")
    print(f"Output: {MAPS_DIR}/")
    print(f"{'='*60}")
    
    for f in sorted(os.listdir(MAPS_DIR)):
        if f.endswith('.png'):
            size_kb = os.path.getsize(f"{MAPS_DIR}/{f}") / 1024
            print(f"  {f}: {size_kb:.0f} KB")
