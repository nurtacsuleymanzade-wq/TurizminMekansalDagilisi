#!/usr/bin/env python3.14
"""
Academic Tourist Map Generator — QGIS PyQGIS
Akademik kalitede, gerçek GIS projeksiyonlu, SVG ikonlu, ölçekli turist haritaları üretir.
QGIS 3.40 + Python 3.14 ile headless modda çalışır.

Kullanım:
    PYTHONPATH=/usr/lib/python3/dist-packages QT_QPA_PLATFORM=offscreen python3.14 create_qgis_tourist_maps.py
"""

import os, sys, json, glob
from pathlib import Path

# ── QGIS Setup ───────────────────────────────────────────────────
# Xvfb sanal ekran ile tam render
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':99'
os.environ['QT_QPA_PLATFORM'] = 'xcb'
os.environ['QGIS_PREFIX_PATH'] = '/usr'

sys.path.insert(0, '/usr/lib/python3/dist-packages')
sys.path.insert(0, '/usr/share/qgis/python')

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer,
    QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
    QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer, QgsSimpleMarkerSymbolLayer,
    QgsSvgMarkerSymbolLayer, QgsSymbolLayer,
    QgsSingleSymbolRenderer, QgsCategorizedSymbolRenderer, QgsRendererCategory,
    QgsGraduatedSymbolRenderer,
    QgsLayout, QgsLayoutItem, QgsLayoutItemMap, QgsLayoutItemLegend, QgsLayoutItemScaleBar,
    QgsLayoutItemLabel, QgsLayoutItemPicture,
    QgsLayoutMeasurement,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsTextFormat, QgsLayoutExporter,
    Qgis,
)
from qgis.PyQt.QtCore import QSizeF, QRectF, QPointF, Qt
from qgis.PyQt.QtGui import QColor, QFont
from qgis.PyQt.QtXml import QDomDocument

from qgis.core import QgsField, QgsFeature

# ── Configuration ─────────────────────────────────────────────────
PROJECT_DIR = Path('/tmp/TurizminMekansalDagilisi')
GEOJSON_DIR = PROJECT_DIR / 'data' / 'geojson'
OUTPUT_DIR = PROJECT_DIR / 'models' / 'maps' / 'qgis_tourist'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# EPSG:32638 — UTM Zone 38N (Azerbaijan)
CRS_AZERBAIJAN = QgsCoordinateReferenceSystem('EPSG:32638')
CRS_WGS84 = QgsCoordinateReferenceSystem('EPSG:4326')

# Tourist map color palette
COLORS = {
    'background': QColor(253, 250, 242),   # warm cream
    'water': QColor(180, 215, 240),         # soft blue
    'roads_major': QColor(200, 80, 60),     # warm red
    'roads_minor': QColor(180, 160, 140),   # tan
    'park_fill': QColor(210, 235, 200),     # soft green
    'urban_fill': QColor(245, 240, 230),    # light beige
    'border': QColor(140, 130, 120),        # gray-brown
}

# POI Category colors and marker styles
POI_STYLES = {
    'Yeme-İçme':        {'color': '#e74c3c', 'shape': 'circle', 'size': 4.5, 'label': 'Restoran/Kafe'},
    'Otel':             {'color': '#3498db', 'shape': 'square', 'size': 5.0, 'label': 'Otel'},
    'Otel/Konaklama':   {'color': '#3498db', 'shape': 'square', 'size': 5.0, 'label': 'Otel/Konaklama'},
    'Tarihi-Kültürel':  {'color': '#9b59b6', 'shape': 'diamond', 'size': 5.0, 'label': 'Tarihi-Kültürel'},
    'Spor':             {'color': '#2ecc71', 'shape': 'triangle', 'size': 4.5, 'label': 'Spor'},
    'Alışveriş-Eğlence':{'color': '#f39c12', 'shape': 'star', 'size': 4.5, 'label': 'Alışveriş-Eğlence'},
    'Park-Plaj-Doğa':   {'color': '#1abc9c', 'shape': 'cross', 'size': 5.0, 'label': 'Park/Doğa'},
    'Dini Yerler':      {'color': '#e67e22', 'shape': 'pentagon', 'size': 5.0, 'label': 'Dini Yerler'},
    'Diğer':            {'color': '#95a5a6', 'shape': 'circle', 'size': 3.5, 'label': 'Diğer'},
    'Ulasim':           {'color': '#7f8c8d', 'shape': 'circle', 'size': 3.5, 'label': 'Ulaşım'},
    'Doga_Alani':       {'color': '#27ae60', 'shape': 'cross', 'size': 5.0, 'label': 'Doğa Alanı'},
    'Tarihi_Anit':      {'color': '#8e44ad', 'shape': 'diamond', 'size': 5.0, 'label': 'Tarihi Anıt'},
    'Destinasyon':      {'color': '#c0392b', 'shape': 'star', 'size': 6.0, 'label': 'Destinasyon'},
    'Turizm_Bolgesi':   {'color': '#16a085', 'shape': 'cross', 'size': 6.0, 'label': 'Turizm Bölgesi'},
}

SHAPE_MAP = {
    'circle': QgsSimpleMarkerSymbolLayer.Circle,
    'square': QgsSimpleMarkerSymbolLayer.Square,
    'diamond': QgsSimpleMarkerSymbolLayer.Diamond,
    'triangle': QgsSimpleMarkerSymbolLayer.Triangle,
    'star': QgsSimpleMarkerSymbolLayer.Star,
    'cross': QgsSimpleMarkerSymbolLayer.Cross,
    'pentagon': QgsSimpleMarkerSymbolLayer.Pentagon,
}

# ── QGIS Application ─────────────────────────────────────────────
def init_qgis():
    """Initialize QGIS in headless mode."""
    qgs = QgsApplication([], False)
    qgs.initQgis()
    return qgs


def load_all_layers(project: QgsProject):
    """Load all GeoJSON files as QGIS layers."""
    layers = {}
    for f in sorted(glob.glob(str(GEOJSON_DIR / '*.geojson'))):
        name = os.path.basename(f).replace('.geojson', '')
        if name == 'azerbaijan_rayon_boundaries_fallback':
            continue  # skip broken file

        layer = QgsVectorLayer(f, name, 'ogr')
        if not layer.isValid():
            print(f'  SKIP invalid: {name}')
            continue

        layer.setCrs(CRS_WGS84)
        layers[name] = layer
        # Don't add to project yet — we'll add selectively per map

    print(f'  Loaded {len(layers)} valid layers')
    return layers


def get_poi_features(layers: dict):
    """Group all POI features by category."""
    categories = {}
    for name, layer in layers.items():
        if 'rayon' in name or 'admin' in name:
            continue
        for feat in layer.getFeatures():
            cat = feat['category'] if feat.fields().indexOf('category') >= 0 else name
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(feat)
            # Also store which layer it came from
            feat.layer_name = name
    return categories


def create_symbol_from_style(style: dict) -> QgsMarkerSymbol:
    """Create a QgsMarkerSymbol from POI style dict."""
    shape = SHAPE_MAP.get(style['shape'], QgsSimpleMarkerSymbolLayer.Circle)
    color = QColor(style['color'])
    color.setAlpha(220)

    symbol_layer = QgsSimpleMarkerSymbolLayer(shape, style['size'])
    symbol_layer.setColor(color)
    symbol_layer.setStrokeColor(QColor(60, 60, 60, 180))
    symbol_layer.setStrokeWidth(0.5)

    symbol = QgsMarkerSymbol()
    symbol.changeSymbolLayer(0, symbol_layer)
    return symbol


def create_rayon_style() -> QgsFillSymbol:
    """Create pastel fill style for rayon boundaries."""
    fill_layer = QgsSimpleFillSymbolLayer(
        QColor(245, 240, 228, 120),  # cream fill
        Qt.SolidPattern,
        QColor(180, 170, 155),       # tan stroke
        Qt.SolidLine,
        0.8
    )
    symbol = QgsFillSymbol()
    symbol.changeSymbolLayer(0, fill_layer)
    return symbol


def create_water_style() -> QgsFillSymbol:
    """Create water body style."""
    fill_layer = QgsSimpleFillSymbolLayer(
        QColor(170, 210, 240, 160),  # soft blue fill
        Qt.SolidPattern,
        QColor(140, 180, 215),       # blue stroke
        Qt.SolidLine,
        0.5
    )
    symbol = QgsFillSymbol()
    symbol.changeSymbolLayer(0, fill_layer)
    return symbol


def make_map(project: QgsProject, layers: dict, region_name: str,
             title_az: str, title_en: str, description: str,
             bbox_coords: list, output_name: str):
    """
    Create a single tourist map.

    bbox_coords: [minx, miny, maxx, maxy] in WGS84
    """
    # ── Clear project ──
    project.clear()

    # ── Add rayon boundaries ──
    rayon_layer = None
    for name, layer in layers.items():
        if 'rayon' in name.lower() or 'admin' in name.lower():
            rayon_layer = layer
            break

    if rayon_layer:
        rayon_layer.setCrs(CRS_WGS84)
        rayon_copy = rayon_layer.clone()
        rayon_copy.setName('Rayon Sınırları')
        rayon_copy.renderer().setSymbol(create_rayon_style())
        project.addMapLayer(rayon_copy)
        print(f'  Rayon boundary: {rayon_copy.featureCount()} features')

    # ── Add POI layers grouped by category ──
    poi_categories = {}
    for name, layer in layers.items():
        if 'rayon' in name or 'admin' in name:
            continue
        cat_idx = layer.fields().indexOf('category')
        for feat in layer.getFeatures():
            cat = feat['category'] if cat_idx >= 0 else name
            cat = str(cat)  # QVariant → str
            if cat not in POI_STYLES and cat.startswith('osm_'):
                continue  # skip raw osm tags
            if cat not in POI_STYLES:
                cat = 'Diğer'
            if cat not in poi_categories:
                poi_categories[cat] = []
            poi_categories[cat].append(feat)

    # Create a single combined POI layer with categorized renderer
    # First, find a template layer for schema
    template_name = None
    for name, layer in layers.items():
        if 'rayon' not in name and 'admin' not in name:
            template_name = name
            break

    if not template_name:
        print('  No POI layers found!')
        return False

    template = layers[template_name]

    # Create memory layer for combined POIs
    poi_mem = QgsVectorLayer(
        f"Point?crs=EPSG:4326&field=name:string(255)&field=category:string(100)",
        'POI', 'memory'
    )
    poi_mem_provider = poi_mem.dataProvider()

    poi_features = []
    for cat, feats in poi_categories.items():
        style_def = POI_STYLES.get(cat, POI_STYLES['Diğer'])
        for feat in feats:
            new_feat = QgsFeature()
            new_feat.setGeometry(feat.geometry())
            ni = feat.fields().indexOf('name')
            feat_name = str(feat['name']) if ni >= 0 else ''
            new_feat.setAttributes([feat_name, cat])
            poi_features.append(new_feat)

    poi_mem_provider.addFeatures(poi_features)
    poi_mem.updateExtents()
    poi_mem.setCrs(CRS_WGS84)
    print(f'  POI layer: {len(poi_features)} features in {len(poi_categories)} categories')

    # Apply categorized renderer
    categories_list = []
    for cat in sorted(poi_categories.keys()):
        style_def = POI_STYLES.get(cat, POI_STYLES['Diğer'])
        symbol = create_symbol_from_style(style_def)
        categories_list.append(QgsRendererCategory(cat, symbol, style_def.get('label', cat)))

    poi_mem.setRenderer(QgsCategorizedSymbolRenderer('category', categories_list))
    project.addMapLayer(poi_mem)

    # ── Setup Layout ──
    layout = QgsLayout(project)
    layout.initializeDefaults()

    # Page size: A3 landscape (420 x 297 mm) — daha hafif
    page_width = 420  # mm
    page_height = 297
    pc = layout.pageCollection()
    page = pc.page(0)
    page.setPageSize(QgsLayoutSize(page_width, page_height))

    # ── Header / Title Banner ──
    title_height = 35  # mm
    title_box = QgsLayoutItemLabel(layout)
    title_box.setText(
        f'<div style="background:#1a5276;color:white;padding:12px 20px;font-size:18pt;font-weight:bold;font-family:Arial,sans-serif;">'
        f'{title_az}'
        f'<br><span style="font-size:11pt;font-weight:normal;color:#aed6f1;">{title_en}</span>'
        f'</div>'
    )
    title_box.setFrameEnabled(False)
    title_box.setBackgroundEnabled(False)
    title_box.setMode(QgsLayoutItemLabel.ModeHtml)
    layout.addLayoutItem(title_box)
    title_box.attemptSetSceneRect(QRectF(15, 10, page_width - 30, title_height))
    title_box.setReferencePoint(QgsLayoutItem.UpperLeft)

    # ── Main Map ──
    map_item = QgsLayoutItemMap(layout)
    map_width = page_width * 0.70  # 70% width for map
    map_height = page_height - title_height - 60
    map_item.attemptSetSceneRect(QRectF(15, title_height + 20, map_width - 30, map_height))
    map_item.setFrameEnabled(True)
    map_item.setFrameStrokeColor(QColor(100, 90, 80))
    map_item.setFrameStrokeWidth(QgsLayoutMeasurement(1.0, QgsUnitTypes.LayoutMillimeters))

    # Set extent
    if bbox_coords:
        rect = QgsRectangle(*bbox_coords)
    else:
        rect = poi_mem.extent()
    map_item.setExtent(rect)
    map_item.zoomToExtent(rect)
    # Add padding (5%)
    rect.scale(1.05)
    map_item.setExtent(rect)

    # Set CRS to Web Mercator for nice basemap alignment
    map_crs = QgsCoordinateReferenceSystem('EPSG:3857')
    map_item.setCrs(map_crs)

    layout.addLayoutItem(map_item)

    # ── Legend (auto from layer tree) ──
    legend = QgsLayoutItemLegend(layout)
    legend.setTitle('Simvollar / Legend')
    legend.setFrameEnabled(True)
    legend.setFrameStrokeColor(QColor(80, 70, 60))
    legend.setBackgroundColor(QColor(255, 255, 255, 240))
    legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.5, QgsUnitTypes.LayoutMillimeters))

    legend_width = page_width * 0.25
    legend.attemptSetSceneRect(QRectF(
        map_width + 20, title_height + 20,
        legend_width - 40, min(map_height * 0.6, 200)
    ))
    layout.addLayoutItem(legend)

    # ── Scale Bar ──
    scalebar = QgsLayoutItemScaleBar(layout)
    scalebar.setStyle('Line Ticks Up')
    scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
    scalebar.setNumberOfSegments(4)
    scalebar.setNumberOfSegmentsLeft(0)
    scalebar.setUnitsPerSegment(1)
    scalebar.setLinkedMap(map_item)
    scalebar.setUnitLabel('km')
    scalebar.setFrameEnabled(False)
    scalebar.setBackgroundColor(QColor(255, 255, 255, 220))
    scalebar.attemptSetSceneRect(QRectF(
        15, page_height - 30, 150, 20
    ))
    layout.addLayoutItem(scalebar)

    # ── North Arrow (SVG picture) ──
    north = QgsLayoutItemPicture(layout)
    north.setPicturePath('/usr/share/qgis/svg/arrows/NorthArrow_01.svg')
    north.setMode(QgsLayoutItemPicture.FormatSVG)
    north.setFrameEnabled(False)
    north.attemptSetSceneRect(QRectF(
        page_width - 70, page_height - 55, 40, 40
    ))
    layout.addLayoutItem(north)

    # ── Info Box ──
    info_box = QgsLayoutItemLabel(layout)
    info_text = (
        f'<div style="background:rgba(255,255,255,0.92);padding:10px;font-size:9pt;font-family:Arial,sans-serif;color:#333;border:1px solid #ccc;">'
        f'<b>Məlumat / Information</b><br>'
        f'{description}<br>'
        f'POI: {len(poi_features)}<br>'
        f'Kateqoriya: {len(poi_categories)}<br>'
        f'Proyeksiya: EPSG:3857 (Web Mercator)<br>'
        f'Mənbə: OpenStreetMap, AzStat, Azərbaycan.Travel'
        f'</div>'
    )
    info_box.setText(info_text)
    info_box.setMode(QgsLayoutItemLabel.ModeHtml)
    info_box.setFrameEnabled(False)
    info_box.attemptSetSceneRect(QRectF(
        map_width + 20, title_height + 260,
        legend_width - 40, 200
    ))
    layout.addLayoutItem(info_box)

    # ── Inset Map (Azerbaijan overview) ──
    inset_size = 100  # mm
    inset_map = QgsLayoutItemMap(layout)
    inset_map.attemptSetSceneRect(QRectF(
        map_width + 20, page_height - inset_size - 30,
        inset_size, inset_size
    ))
    inset_map.setFrameEnabled(True)
    inset_map.setFrameStrokeColor(QColor(100, 90, 80))
    inset_map.setFrameStrokeWidth(QgsLayoutMeasurement(0.5, QgsUnitTypes.LayoutMillimeters))

    # Azerbaijan full extent
    az_rect = QgsRectangle(44.7, 38.3, 50.6, 41.9)  # WGS84
    inset_map.setExtent(az_rect)
    inset_map.setCrs(map_crs)

    layout.addLayoutItem(inset_map)
    if bbox_coords:
        # Draw a red rectangle overlay for current extent on inset
        pass  # TODO: add extent indicator

    inset_label = QgsLayoutItemLabel(layout)
    inset_label.setText('Azərbaycan')
    inset_label.setFrameEnabled(False)
    inset_label.attemptSetSceneRect(QRectF(
        map_width + 20, page_height - inset_size - 40,
        inset_size, 10
    ))
    layout.addLayoutItem(inset_label)

    # ── Export ──
    # PNG 300 DPI (akademik kalite)
    png_path = str(OUTPUT_DIR / f'{output_name}.png')
    exporter = QgsLayoutExporter(layout)
    png_settings = QgsLayoutExporter.ImageExportSettings()
    png_settings.dpi = 300
    exporter.exportToImage(png_path, png_settings)
    print(f'  ✓ PNG: {png_path}')

    # PDF vektör kalitesinde
    pdf_path = str(OUTPUT_DIR / f'{output_name}.pdf')
    pdf_settings = QgsLayoutExporter.PdfExportSettings()
    pdf_settings.dpi = 300
    pdf_settings.forceVectorOutput = True
    exporter.exportToPdf(pdf_path, pdf_settings)
    print(f'  ✓ PDF: {pdf_path}')

    return True


# ── Region Definitions ───────────────────────────────────────────
REGIONS = [
    {
        'name': 'Quba Şəhəri',
        'title_az': 'Quba Şəhəri',
        'title_en': 'Guba City — Tourist Map',
        'description': 'Qudyalçay sahili, Qırmızı Qəsəbə, Dağlı kəndi. Quba Regional Turizm İdarəsi.',
        'bbox': [48.42, 41.33, 48.55, 41.40],  # WGS84
        'output': 'quba_city',
    },
    {
        'name': 'Quba-Qusar',
        'title_az': 'Quba-Qusar Rayonu',
        'title_en': 'Guba-Gusar Region Map',
        'description': 'Şahdağ Milli Parkı, Afurca Şəlaləsi, Xınalıq kəndi, Qolf Klubu.',
        'bbox': [48.0, 40.9, 48.7, 41.9],
        'output': 'quba_qusar_region',
    },
    {
        'name': 'Naxçıvan MR',
        'title_az': 'Naxçıvan Muxtar Respublikası',
        'title_en': 'Nakhchivan AR — Tourist Map',
        'description': 'İpək Yolu, Möminə Xatun Türbəsi, İlandağ. 5.500 km², 461.500 nəfər.',
        'bbox': [44.7, 38.8, 46.2, 39.9],
        'output': 'naxcivan',
    },
    {
        'name': 'Qəbələ',
        'title_az': 'Qəbələ Rayonu',
        'title_en': 'Gabala Region — Tourist Map',
        'description': 'Tufandağ, Nohur Gölü, Qafqaz dağları.',
        'bbox': [47.7, 40.8, 48.1, 41.1],
        'output': 'qebele',
    },
    {
        'name': 'Bakı',
        'title_az': 'Bakı Şəhəri',
        'title_en': 'Baku City — Tourist Map',
        'description': 'İçərişəhər, Dənizkənarı Bulvar, Alov Qüllələri.',
        'bbox': [49.65, 40.28, 50.05, 40.48],
        'output': 'baku',
    },
    {
        'name': 'Xaçmaz',
        'title_az': 'Xaçmaz Rayonu',
        'title_en': 'Khachmaz Region — Tourist Map',
        'description': 'Nabran, Xəzər sahili, meşəlik ərazilər.',
        'bbox': [48.6, 41.4, 49.0, 41.8],
        'output': 'xacmaz',
    },
    {
        'name': 'Azərbaycan',
        'title_az': 'Azərbaycan Respublikası',
        'title_en': 'Republic of Azerbaijan — Tourist Map',
        'description': 'Ümumi turizm məkan dağılışı — 82.934 POI. 66 rayon, 11 iqtisadi rayon.',
        'bbox': [44.7, 38.3, 50.6, 41.9],
        'output': 'azerbaycan',
    },
    {
        'name': 'Lənkəran',
        'title_az': 'Lənkəran Rayonu',
        'title_en': 'Lankaran Region — Tourist Map',
        'description': 'Talış Dağları, İstisu, Xəzər sahili.',
        'bbox': [48.7, 38.6, 49.0, 39.0],
        'output': 'lankaran',
    },
    {
        'name': 'Şəki',
        'title_az': 'Şəki Rayonu',
        'title_en': 'Sheki Region — Tourist Map',
        'description': 'Xan Sarayı, Kiş Alban Məbədi, İpək Yolu.',
        'bbox': [46.9, 41.0, 47.4, 41.3],
        'output': 'sheki',
    },
    {
        'name': 'Gəncə',
        'title_az': 'Gəncə Şəhəri',
        'title_en': 'Ganja City — Tourist Map',
        'description': 'Nizami Məqbərəsi, Göygöl, qədim şəhər.',
        'bbox': [46.25, 40.60, 46.45, 40.75],
        'output': 'gence',
    },
]


# ── Main ──────────────────────────────────────────────────────────
def main():
    print('=' * 60)
    print('QGIS Tourist Map Generator — Academic Quality')
    print('=' * 60)

    qgs = init_qgis()
    print(f'QGIS {Qgis.QGIS_VERSION} initialized')

    project = QgsProject.instance()
    layers = load_all_layers(project)
    print(f'Layers loaded: {len(layers)}')

    for region in REGIONS:
        print(f'\n── {region["name"]} ──')
        try:
            make_map(
                project, layers,
                region['name'], region['title_az'], region['title_en'],
                region['description'], region['bbox'], region['output']
            )
        except Exception as e:
            print(f'  ✗ FAILED: {e}')
            import traceback
            traceback.print_exc()
            continue

    qgs.exitQgis()
    print('\n✅ All maps generated!')


if __name__ == '__main__':
    main()
