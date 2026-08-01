#!/usr/bin/env python3
"""
BROCHURE STYLE Tourist Map Generator — Quba Broşür Stili
Akademik kalitede, açık pastel tonlu, ikonlu, iki dilli turist haritaları.
QGIS yerine matplotlib + contextily + gerçek POI verisiyle.
"""

import json, os, warnings, math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, FancyBboxPatch
import matplotlib.font_manager as fm
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, box, Polygon, LineString
import contextily as ctx
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

warnings.filterwarnings('ignore')

# ── Config ──────────────────────────────────────────────────
DATA_DIR = "data/geojson"
MAPS_DIR = "models/maps/tourist_v2"
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
# Light pastels matching the Quba tourist brochure aesthetic
BG_CREAM    = '#faf6ee'    # Map background
BG_LIGHTER  = '#fdfcf8'    # Outer/paper background
HEADER_BG   = '#f0ebe0'    # Light header band
FRAME_COLOR = '#c4b9a8'    # Decorative border

# Pastel region fills
REGION_COLORS = ['#e8efe4', '#f2edd5', '#e8e2ed', '#ede3d5',
                 '#d8ede2', '#f0e8e3', '#e2eced', '#ede8d8',
                 '#e3e6f0', '#f0e2e3', '#d5eddc', '#edd6eb',
                 '#e6edda', '#f0ece0']

# Category colors — vibrant tourist map icons
CATEGORIES = {
    "Yeme-İçme":       {"color": "#e74c3c", "icon": "🍽",  "label": "Restoran / Kafe / Food",       "marker": "s"},
    "Otel/Konaklama":  {"color": "#8e44ad", "icon": "🏨",  "label": "Otel / Hotel / Accommodation",  "marker": "D"},
    "Tarihi-Kültürel": {"color": "#2980b9", "icon": "🏛",  "label": "Muzey / Tarixi Abidə / Museum", "marker": "o"},
    "Spor":            {"color": "#27ae60", "icon": "⚽",  "label": "İdman / Sport",                  "marker": "p"},
    "Alışveriş-Eğlence":{"color": "#e67e22","icon": "🛍",  "label": "Alış-veriş / Shopping",          "marker": "h"},
    "Park-Plaj-Doğa":  {"color": "#16a085", "icon": "🌳",  "label": "Park / Çimərlik / Təbiət",       "marker": "^"},
    "Dini Yerler":     {"color": "#c0392b", "icon": "🕌",  "label": "Dini Abidə / Religious",         "marker": "*"},
}

# ── REGION DEFINITIONS ──────────────────────────────────────
REGIONS = {
    "quba_tourist": {
        "title_az": "QUBA ŞƏHƏRİ",
        "title_en": "GUBA CITY — TOURIST MAP",
        "subtitle": "Quba Regional Turizm İdarəsi | Tourism Information Center",
        "bounds": [48.44, 41.32, 48.56, 41.40],
        "photo_label": "Qırmızı Qəsəbə / Red Town",
    },
    "quba_qusar_region": {
        "title_az": "QUBA-QUSAR RAYONU",
        "title_en": "GUBA-GUSAR REGION",
        "subtitle": "Şahdağ Milli Parkı • Afurca Şəlaləsi • Xınalıq kəndi",
        "bounds": [47.8, 40.8, 48.8, 41.7],
        "photo_label": "Şahdağ / Shahdag Mountain Resort",
    },
    "naxcivan_tourist": {
        "title_az": "NAXÇIVAN MUXTAR RESPUBLİKASI",
        "title_en": "NAKHCHIVAN A.R. — TOURIST MAP",
        "subtitle": "Tarixi İpək Yolu • Möminə Xatun Türbəsi • İlandağ",
        "bounds": [44.5, 38.8, 46.2, 39.9],
        "photo_label": "Möminə Xatun / Momine Khatun Mausoleum",
    },
    "qebele_tourist": {
        "title_az": "QƏBƏLƏ RAYONU",
        "title_en": "GABALA REGION",
        "subtitle": "Qafqazın İncisi • Tufandağ • Nohur Gölü",
        "bounds": [47.5, 40.7, 48.2, 41.2],
        "photo_label": "Tufandağ / Tufandag Resort",
    },
    "baku_tourist": {
        "title_az": "BAKI ŞƏHƏRİ",
        "title_en": "BAKU CITY",
        "subtitle": "İçərişəhər • Bulvar • Qız Qalası / Old City • Boulevard • Maiden Tower",
        "bounds": [49.4, 40.1, 50.1, 40.6],
        "photo_label": "İçərişəhər / Icherisheher (UNESCO)",
    },
    "xacmaz_tourist": {
        "title_az": "XAÇMAZ RAYONU",
        "title_en": "KHACHMAZ REGION",
        "subtitle": "Xəzər Sahili • Nabran • Meşəliklər / Caspian Coast • Forests",
        "bounds": [48.5, 41.3, 49.2, 41.8],
        "photo_label": "Nabran / Nabran Beach Resort",
    },
    "azerbaycan_tourist": {
        "title_az": "AZƏRBAYCAN RESPUBLİKASI",
        "title_en": "REPUBLIC OF AZERBAIJAN",
        "subtitle": "Turizmin Mekansal Dağılışı — Doktora Tezi",
        "bounds": None,
        "photo_label": "Azərbaycan Xəritəsi",
    },
    "lankaran_tourist": {
        "title_az": "LƏNKƏRAN RAYONU",
        "title_en": "LANKARAN REGION",
        "subtitle": "Xəzər Sahili • Talış Dağları • İstisu",
        "bounds": [48.5, 38.5, 49.1, 39.0],
        "photo_label": "Lənkəran / Lankaran City",
    },
    "sheki_tourist": {
        "title_az": "ŞƏKİ RAYONU",
        "title_en": "SHEKI REGION",
        "subtitle": "Xan Sarayı • Kiş Alban Məbədi • Karvansaray",
        "bounds": [47.0, 40.9, 47.5, 41.4],
        "photo_label": "Şəki Xan Sarayı / Sheki Khan Palace (UNESCO)",
    },
    "gence_tourist": {
        "title_az": "GƏNCƏ ŞƏHƏRİ",
        "title_en": "GANJA CITY",
        "subtitle": "Qədim Şəhər • Göygöl • Nizami Məqbərəsi",
        "bounds": [46.1, 40.5, 46.5, 40.8],
        "photo_label": "Nizami Məqbərəsi / Nizami Mausoleum",
    },
}

# ── STYLING FUNCTIONS ────────────────────────────────────────

def add_brochure_header(fig, ax, region_info, xlim, ylim):
    """Pastel creamy header band matching Quba brochure style."""
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    # Header band — wide cream bar
    header_h = y_range * 0.14
    rect = FancyBboxPatch(
        (xlim[0] - x_range * 0.02, ylim[1] + y_range * 0.01),
        x_range * 1.04, header_h,
        boxstyle="round,pad=0.005",
        facecolor=HEADER_BG, edgecolor=FRAME_COLOR,
        linewidth=1.2, alpha=0.95, zorder=95
    )
    ax.add_patch(rect)

    # Main title — bold, dark
    center_x = (xlim[0] + xlim[1]) / 2
    ax.text(center_x, ylim[1] + y_range * 0.01 + header_h * 0.65,
            region_info['title_az'],
            fontsize=16, color='#2c3e50', fontweight='bold',
            ha='center', va='center', zorder=96,
            fontfamily='sans-serif')

    # English title
    ax.text(center_x, ylim[1] + y_range * 0.01 + header_h * 0.35,
            region_info['title_en'],
            fontsize=10, color='#7f8c8d', fontweight='normal',
            ha='center', va='center', zorder=96,
            fontfamily='sans-serif', style='italic')

    # Subtitle / tagline
    ax.text(center_x, ylim[1] + y_range * 0.01 + header_h * 0.10,
            region_info['subtitle'],
            fontsize=7, color='#95a5a6',
            ha='center', va='bottom', zorder=96)


def add_scale_bar(ax, xlim, ylim, distance_km):
    """Clean scale bar with tick marks."""
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    # Position bottom-left
    bar_x = xlim[0] + x_range * 0.05
    bar_y = ylim[0] + y_range * 0.04
    dist_m = distance_km * 1000

    # Main bar
    ax.plot([bar_x, bar_x + dist_m], [bar_y, bar_y], '-',
            color='#2c3e50', lw=4, solid_capstyle='butt', zorder=50, alpha=0.9)

    # End ticks
    tick_h = y_range * 0.008
    for xx in [bar_x, bar_x + dist_m]:
        ax.plot([xx, xx], [bar_y - tick_h, bar_y + tick_h], '-',
                color='#2c3e50', lw=1.5, solid_capstyle='butt', zorder=50)

    # Half tick
    ax.plot([bar_x + dist_m/2, bar_x + dist_m/2], [bar_y - tick_h*0.6, bar_y + tick_h*0.6],
            '-', color='#2c3e50', lw=1.0, zorder=50)

    # Labels
    ax.text(bar_x, bar_y - y_range * 0.012, '0',
            ha='center', va='top', fontsize=8, fontweight='bold',
            color='#2c3e50', zorder=51)
    ax.text(bar_x + dist_m/2, bar_y - y_range * 0.012, f'{distance_km/2:.0f}',
            ha='center', va='top', fontsize=7, color='#555555', zorder=51)
    ax.text(bar_x + dist_m, bar_y - y_range * 0.012, f'{distance_km} km',
            ha='center', va='top', fontsize=8, fontweight='bold',
            color='#2c3e50', zorder=51)


def add_north_arrow(ax, xlim, ylim):
    """Simple elegant north arrow."""
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    arrow_x = xlim[1] - x_range * 0.08
    arrow_y = ylim[1] - y_range * 0.10
    arrow_len = y_range * 0.04

    ax.annotate('N', xy=(arrow_x, arrow_y + arrow_len),
                xytext=(arrow_x, arrow_y),
                ha='center', va='center',
                fontsize=13, fontweight='bold', color='#2c3e50',
                arrowprops=dict(arrowstyle='->', color='#2c3e50',
                               lw=2.5, alpha=0.9),
                zorder=50)


def add_legend_panel(ax, region_pois, xlim, ylim):
    """Clean legend panel — matching brochure style."""
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    # Position top-right
    box_x = xlim[1] - x_range * 0.26
    box_y = ylim[0] + y_range * 0.02
    box_w = x_range * 0.24
    box_h = y_range * 0.36

    rect = FancyBboxPatch(
        (box_x, box_y), box_w, box_h,
        boxstyle="round,pad=0.015",
        facecolor='white', edgecolor=FRAME_COLOR,
        linewidth=1.0, alpha=0.95, zorder=100
    )
    ax.add_patch(rect)

    # Legend title
    ax.text(box_x + box_w * 0.5, box_y + box_h - y_range * 0.018,
            "ŞƏRTİ İŞARƏLƏR", fontsize=9,
            color='#2c3e50', fontweight='bold', ha='center', zorder=101)
    ax.text(box_x + box_w * 0.5, box_y + box_h - y_range * 0.035,
            "Conventional Signs / Legend", fontsize=6.5,
            color='#7f8c8d', ha='center', zorder=101, style='italic')

    y_pos = box_y + box_h - y_range * 0.055

    for cat_name, cfg in CATEGORIES.items():
        cnt = len(region_pois[region_pois['category'] == cat_name])
        if cnt == 0:
            continue

        # Icon marker
        icon_size = 120
        ax.scatter([box_x + box_w * 0.10], [y_pos],
                   marker=cfg['marker'], s=icon_size,
                   color=cfg['color'], edgecolors='white',
                   linewidth=0.8, alpha=0.9, zorder=101)

        # Label
        ax.text(box_x + box_w * 0.22, y_pos,
                f"{cfg['icon']} {cfg['label']}  ({cnt})",
                fontsize=6.5, color='#333333', zorder=101,
                va='center', fontfamily='sans-serif')

        y_pos -= y_range * 0.032

    # Data source note
    ax.text(box_x + box_w * 0.5, y_pos - y_range * 0.005,
            "Mənbə: AzStat 2025, OSM",
            fontsize=5.5, color='#aaaaaa', ha='center', zorder=101,
            style='italic')


def add_photo_placeholder(ax, region_info, xlim, ylim):
    """Add a decorative photo frame area (right side)."""
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    # Position right side
    photo_x = xlim[1] - x_range * 0.28
    photo_y = ylim[0] + y_range * 0.40
    photo_w = x_range * 0.26
    photo_h = y_range * 0.55

    rect = FancyBboxPatch(
        (photo_x, photo_y), photo_w, photo_h,
        boxstyle="round,pad=0.015",
        facecolor='#f5f0e8', edgecolor=FRAME_COLOR,
        linewidth=1.5, alpha=0.9, zorder=98
    )
    ax.add_patch(rect)

    # Inner frame
    inner_margin = x_range * 0.006
    rect2 = Rectangle(
        (photo_x + inner_margin, photo_y + inner_margin),
        photo_w - 2*inner_margin, photo_h - 2*inner_margin,
        facecolor=BG_CREAM, edgecolor='#d0c8b8',
        linewidth=0.5, alpha=0.7, zorder=99
    )
    ax.add_patch(rect2)

    # Placeholder text
    ax.text(photo_x + photo_w/2, photo_y + photo_h/2,
            "📷", fontsize=28, ha='center', va='center',
            color='#cccccc', zorder=99)
    ax.text(photo_x + photo_w/2, photo_y + photo_h/2 - y_range * 0.03,
            region_info.get('photo_label', ''),
            fontsize=5, color='#bbbbbb', ha='center', va='top',
            zorder=99, style='italic')

    # Caption
    ax.text(photo_x + photo_w/2, photo_y - y_range * 0.012,
            region_info.get('photo_label', ''),
            fontsize=5.5, color='#888888', ha='center', va='top',
            zorder=99, fontfamily='sans-serif')


def create_tourist_map(region_key, region_info):
    """Generate a single tourist brochure-style map."""
    print(f"\n{'='*60}")
    print(f"Region: {region_key} → {region_info['title_az']}")

    # Figure setup — generous size for brochure feel
    bounds = region_info['bounds']

    if bounds is None:
        fig_w, fig_h = 18, 14
        xlim = (country.total_bounds[0], country.total_bounds[2])
        ylim = (country.total_bounds[1], country.total_bounds[3])
    else:
        b = bounds
        bounds_3857 = gpd.GeoDataFrame(
            {'geometry': [box(*b)]}, crs="EPSG:4326"
        ).to_crs("EPSG:3857")
        bbox = bounds_3857.total_bounds
        xlim = (bbox[0], bbox[2])
        ylim = (bbox[1], bbox[3])

        aspect = (bbox[2] - bbox[0]) / (bbox[3] - bbox[1])
        fig_w = max(14, 12 * aspect)
        fig_h = max(10, fig_w / aspect * 0.9)

    fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))
    fig.patch.set_facecolor(BG_LIGHTER)
    ax.set_facecolor(BG_CREAM)

    # Expand limits slightly for header/footer
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]
    pad_x = x_range * 0.06
    pad_y = y_range * 0.16
    ax.set_xlim(xlim[0] - pad_x, xlim[1] + pad_x)
    ax.set_ylim(ylim[0] - pad_y, ylim[1] + pad_y * 0.8)
    new_xlim = ax.get_xlim()
    new_ylim = ax.get_ylim()

    # ── BASEMAP — Very light CartoDB ──
    zoom = 11 if bounds is None else max(8, int(14 - abs(bounds[2]-bounds[0])*4))
    try:
        ctx.add_basemap(ax, crs=country.crs,
                       source=ctx.providers.CartoDB.PositronNoLabels,
                       alpha=0.4, zoom=zoom)
    except Exception:
        try:
            ctx.add_basemap(ax, crs=country.crs,
                           source=ctx.providers.CartoDB.Positron,
                           alpha=0.3, zoom=zoom)
        except Exception:
            country.plot(ax=ax, color='#ece4d8', edgecolor='#cccccc', lw=0.3)
            print("  No basemap — fallback fill")

    # ── RAYON BOUNDARIES ──
    try:
        rayons.plot(ax=ax, facecolor='none', edgecolor='#b8a898',
                   linewidth=0.6, alpha=0.5, linestyle='--')
        print("  Rayon boundaries OK")
    except Exception as e:
        print(f"  Rayons: {e}")

    # ── REGION FILL ──
    if bounds is not None:
        try:
            region_rayons = rayons.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]]
            for i, (idx, row) in enumerate(region_rayons.iterrows()):
                color = REGION_COLORS[i % len(REGION_COLORS)]
                if row.geometry is not None:
                    gpd.GeoSeries([row.geometry]).plot(
                        ax=ax, color=color, alpha=0.35,
                        edgecolor='#c0b8a8', linewidth=0.4
                    )

            # Region labels
            for idx, row in region_rayons.iterrows():
                centroid = row.geometry.centroid
                name = row.get('adm1_name1', row.get('adm1_name', ''))
                if name and xlim[0] <= centroid.x <= xlim[1] and ylim[0] <= centroid.y <= ylim[1]:
                    ax.text(centroid.x, centroid.y, name,
                           fontsize=7.5, color='#8a8070', ha='center',
                           va='center', alpha=0.6, fontweight='bold',
                           style='italic')
            print(f"  Region fill: {len(region_rayons)} rayons")
        except Exception as e:
            print(f"  Region fill: {e}")

    # ── COUNTRY BORDER (if visible) ──
    country.plot(ax=ax, facecolor='none', edgecolor='#8a7a6a',
                linewidth=1.2, alpha=0.7, linestyle='-')

    # ── POI MARKERS — Larger, distinct shapes ──
    region_pois = pois.cx[xlim[0]:xlim[1], ylim[0]:ylim[1]] if bounds else pois
    print(f"  POIs in view: {len(region_pois):,}")

    # Calculate optimal marker size based on map extent
    if bounds is None:
        marker_size = 40
    elif x_range < 15000:
        marker_size = 80
    elif x_range < 50000:
        marker_size = 55
    elif x_range < 100000:
        marker_size = 40
    else:
        marker_size = 25

    for cat_name, cfg in CATEGORIES.items():
        cat_pois = region_pois[region_pois['category'] == cat_name]
        if len(cat_pois) == 0:
            continue

        cat_pois.plot(
            ax=ax,
            color=cfg['color'],
            marker=cfg['marker'],
            markersize=marker_size,
            edgecolor='white',
            linewidth=0.6,
            alpha=0.85,
            zorder=8,
            label=cfg['label']
        )

    # ── POI LABELS — Smart labeling for key POIs ──
    # Show labels for POIs with meaningful names (not auto-generated)
    named_pois = region_pois[~region_pois['name'].str.contains('#', na=False)]
    named_pois = named_pois[named_pois['name'].str.len() > 3]

    # Limit to ~15 most important based on subcategory
    if len(named_pois) > 0:
        important = named_pois[named_pois['subcategory'].notna()]
        if len(important) < 8:
            important = named_pois

        shown = 0
        for idx, row in important.iterrows():
            if shown > 18:
                break
            try:
                geom = row.geometry
                if hasattr(geom, 'x'):
                    pt = (geom.x, geom.y)
                else:
                    continue

                # Offset label so it doesn't overlap marker
                label_offset = y_range * 0.008
                ax.annotate(
                    row['name'][:25],
                    xy=pt,
                    xytext=(pt[0], pt[1] + label_offset),
                    fontsize=5.5, color='#333333',
                    ha='center', va='bottom',
                    zorder=10,
                    alpha=0.75,
                    fontfamily='sans-serif',
                    bbox=dict(boxstyle='round,pad=0.15',
                             facecolor='white', edgecolor='none',
                             alpha=0.6)
                )
                shown += 1
            except Exception:
                continue
        print(f"  Labels: {shown}")

    # ── DECORATIONS ──
    add_brochure_header(fig, ax, region_info, xlim, ylim)

    # Scale bar
    if bounds is None:
        scale_km = 100
    elif x_range < 15000:
        scale_km = 2
    elif x_range < 50000:
        scale_km = 5
    elif x_range < 100000:
        scale_km = 10
    else:
        scale_km = 20
    add_scale_bar(ax, new_xlim, new_ylim, scale_km)

    # North arrow
    add_north_arrow(ax, new_xlim, new_ylim)

    # Legend
    add_legend_panel(ax, region_pois, new_xlim, new_ylim)

    # Photo placeholder
    add_photo_placeholder(ax, region_info, new_xlim, new_ylim)

    # ── FRAME ──
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(FRAME_COLOR)
        spine.set_linewidth(2.5)

    # ── FOOTER ──
    fig.text(0.5, 0.008,
             "Turizmin Mekansal Dağılışı — Doktora Tezi | Məlumat mənbəyi: AzStat 2025, OpenStreetMap | © N.T.Süleymanzadə, AzTU 2026",
             ha='center', fontsize=6.5, color='#aaaaaa', style='italic')

    # ── SAVE ──
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect('equal')

    out_path = f"{MAPS_DIR}/{region_key}.png"
    fig.savefig(out_path, dpi=300, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')

    size_mb = os.path.getsize(out_path) / (1024 * 1024)
    print(f"  ✓ Saved: {out_path} ({size_mb:.1f} MB)")
    plt.close(fig)
    return out_path


# ── MAIN ─────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("  TOURIST BROCHURE MAP GENERATOR v2")
    print("  Quba Broşür Stili — Akademik Haritalar")
    print("=" * 60)

    for key, info in REGIONS.items():
        create_tourist_map(key, info)

    print(f"\n{'='*60}")
    print("  ALL MAPS GENERATED!")
    print(f"  Output: {MAPS_DIR}/")

    for f in sorted(os.listdir(MAPS_DIR)):
        if f.endswith('.png'):
            size_kb = os.path.getsize(f"{MAPS_DIR}/{f}") / 1024
            print(f"    {f}: {size_kb:.0f} KB")
    print(f"{'='*60}")
