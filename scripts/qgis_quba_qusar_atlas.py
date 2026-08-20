#!/usr/bin/env python3
"""QGIS-native atlas-style Quba–Qusar tourism map.
Run with: PYTHONPATH=/usr/lib/python3/dist-packages xvfb-run -a -s '-screen 0 1800x1400x24' qgis --noplugins --code thisfile --noversioncheck
"""
from qgis.core import *
from qgis.PyQt.QtCore import Qt, QRectF
from qgis.PyQt.QtGui import QColor, QFont
from pathlib import Path
import os

# Standalone PyQGIS bootstrap (the distro's qgis GUI wrapper has a separate Python path).
QgsApplication.setPrefixPath('/usr', True)
qgs = QgsApplication([], False)
qgs.initQgis()

ROOT = Path('/tmp/tmd')
DATA = ROOT/'data'/'geojson'
OUT = ROOT/'models'/'maps'/'qgis_atlas'
OUT.mkdir(parents=True, exist_ok=True)
PNG = OUT/'quba_qusar_qgis_atlas.png'
PDF = OUT/'quba_qusar_qgis_atlas.pdf'
QGZ = OUT/'quba_qusar_qgis_atlas.qgz'

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'))

# Light OSM basemap: a real geospatial tile layer, kept subordinate to vector content.
xyz_uri = 'type=xyz&url=https://tile.openstreetmap.org/{z}/{x}/{y}.png&zmin=0&zmax=19'
basemap = QgsRasterLayer(xyz_uri, 'Əsas xəritə — OpenStreetMap', 'wms')
if basemap.isValid():
    project.addMapLayer(basemap)

# Helper for vector layers.
def vec(filename, name, subset=None):
    lyr = QgsVectorLayer(str(DATA/filename), name, 'ogr')
    if not lyr.isValid():
        print('INVALID', filename); return None
    lyr.setCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
    if subset: lyr.setSubsetString(subset)
    project.addMapLayer(lyr)
    return lyr

def fill_layer(lyr, fill, stroke, width=0.5):
    sym = QgsFillSymbol.createSimple({'color':fill, 'outline_color':stroke, 'outline_width':str(width)})
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))

def line_layer(lyr, color, width=0.6, dash=None):
    sym = QgsLineSymbol.createSimple({'line_color':color, 'line_width':str(width)})
    if dash: sym.symbolLayer(0).setPenStyle(Qt.DashLine)
    lyr.setRenderer(QgsSingleSymbolRenderer(sym))

def point_categorized(lyr):
    cats=[]
    defs=[
        ('Destinasyon','#b2182b','star','5.2','Destinasiya / Destination'),
        ('Turizm_Bolgesi','#2166ac','triangle','4.8','Turizm bölgəsi / Tourism region'),
        ('Tarihi_Anit','#762a83','diamond','4.4','Tarixi abidə / Historic site'),
        ('Doga_Alani','#1b7837','circle','4.2','Təbiət obyekti / Natural site'),
        ('Otel','#d95f02','square','3.8','Otel / Hotel'),
        ('Kultur_Merkezi','#8c6bb1','pentagon','4.0','Mədəniyyət mərkəzi / Cultural centre'),
        ('Diger_Tesis','#e6ab02','hexagon','3.8','Digər obyekt / Other facility'),
        ('Ulasim','#1f78b4','cross','4.0','Nəqliyyat / Transport'),
    ]
    for value,color,shape,size,label in defs:
        s=QgsMarkerSymbol.createSimple({'name':shape,'color':color,'outline_color':'white','outline_width':'0.7','size':size})
        cats.append(QgsRendererCategory(value,s,label))
    lyr.setRenderer(QgsCategorizedSymbolRenderer('category',cats))

def labels(lyr, field, size=10, color='#202020', bold=False):
    s=QgsPalLayerSettings(); s.fieldName=field; s.enabled=True
    s.placement=QgsPalLayerSettings.Placement.OverPoint
    tf=QgsTextFormat(); tf.setFont(QFont('DejaVu Serif',int(size))); tf.setColor(QColor(color)); tf.setSize(size)
    if bold: tf.setFontWeight(QFont.Bold)
    buf=QgsTextBufferSettings(); buf.setEnabled(True); buf.setSize(1.2); buf.setColor(QColor('white')); tf.setBuffer(buf)
    s.setFormat(tf); lyr.setLabelsEnabled(True); lyr.setLabeling(QgsVectorLayerSimpleLabeling(s))

# District polygons: selected Quba/Qusar receive muted atlas colors; nearby districts are only outlines.
allray = vec('azerbaijan_rayon_boundaries.geojson','Rayon sərhədləri')
if allray:
    fill_layer(allray,'#f6f0df','#927b68',0.45)
    # Label the two focus rayons by centroid via existing center fields is not possible on polygon labels; use admin points below.
focus = vec('azerbaijan_rayon_boundaries.geojson','Quba və Qusar rayonları', '\"adm1_name1\" IN (\'Quba\',\'Qusar\')')
if focus:
    fill_layer(focus,'#dcebc4','#604c3a',1.0)
    focus.setOpacity(0.22)
# Administrative line layer adds the restrained atlas boundary network.
adm = vec('aze_adminlines.geojson','İnzibati sərhədlər')
if adm: line_layer(adm,'#b36b5c',0.55,True)

# Real tourism inventory; all eight source categories are retained and symbolized explicitly.
poi = vec('all_tourism_points.geojson','Turizm obyektləri')
if poi: point_categorized(poi)
# City/admin points provide labels without showing thousands of raw OSM POIs.
adminpts = vec('aze_adminpoints.geojson','Şəhər və yaşayış məntəqələri')
if adminpts:
    labels(adminpts,'name',8.5,'#222222',False)

# Layout: A3 landscape, map left and a clean legend/metadata column right.
layout=QgsPrintLayout(project); layout.initializeDefaults(); layout.setName('Quba–Qusar Atlas Turizm Xəritəsi')
page=layout.pageCollection().page(0); page.setPageSize(QgsLayoutSize(420,297))

def label(text,x,y,w,h,fs=12,color='#1a5276',bold=False,align=Qt.AlignLeft):
    i=QgsLayoutItemLabel(layout); i.setText(text); i.setFrameEnabled(False); i.setHAlign(align); i.setVAlign(Qt.AlignVCenter)
    f=QFont('DejaVu Serif',int(fs));
    if bold: f.setBold(True)
    tf=QgsTextFormat(); tf.setFont(f); tf.setColor(QColor(color)); tf.setSize(fs)
    i.setTextFormat(tf); i.attemptMove(QgsLayoutPoint(x,y,QgsUnitTypes.LayoutMillimeters)); i.attemptResize(QgsLayoutSize(w,h)); layout.addLayoutItem(i); return i

# Cream paper header and title.
header=QgsLayoutItemShape(layout); header.setShapeType(QgsLayoutItemShape.Rectangle); header.attemptMove(QgsLayoutPoint(0,0,QgsUnitTypes.LayoutMillimeters)); header.attemptResize(QgsLayoutSize(420,23)); header.setBrush(QColor('#f5f0e8')); header.setPen(QColor('#f5f0e8')); layout.addLayoutItem(header)
label('QUBA–QUSAR',12,3,180,10,19,'#1a5276',True)
label('Turizm fəaliyyətlərinin məkan xəritəsi',12,12,220,7,10,'#5b4636',False)
label('QGIS atlas üslubu  |  EPSG:3857',280,7,125,7,7.5,'#5b4636',False,Qt.AlignRight)

map_item=QgsLayoutItemMap(layout); map_item.attemptMove(QgsLayoutPoint(10,29,QgsUnitTypes.LayoutMillimeters)); map_item.attemptResize(QgsLayoutSize(300,250)); map_item.setFrameEnabled(True); map_item.setFrameStrokeColor(QColor('#604c3a')); map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.7,QgsUnitTypes.LayoutMillimeters))
# Quba–Qusar plus surrounding route context.
ext=QgsRectangle(47.65,40.70,49.10,42.05); tr=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), QgsCoordinateReferenceSystem('EPSG:3857'), project.transformContext()); ext=tr.transformBoundingBox(ext); map_item.setExtent(ext); layout.addLayoutItem(map_item)

# Right panel background.
panel=QgsLayoutItemShape(layout); panel.setShapeType(QgsLayoutItemShape.Rectangle); panel.attemptMove(QgsLayoutPoint(318,29,QgsUnitTypes.LayoutMillimeters)); panel.attemptResize(QgsLayoutSize(92,250)); panel.setBrush(QColor('#fbfaf6')); panel.setPen(QColor('#d0c2b2')); layout.addLayoutItem(panel)
label('ŞƏRTİ İŞARƏLƏR',325,36,78,8,11,'#1a5276',True,Qt.AlignCenter)
# Legend linked to map.
leg=QgsLayoutItemLegend(layout); leg.setTitle(''); leg.setLinkedMap(map_item); leg.setAutoUpdateModel(True); leg.setFrameEnabled(False); leg.attemptMove(QgsLayoutPoint(325,47,QgsUnitTypes.LayoutMillimeters)); leg.attemptResize(QgsLayoutSize(78,90)); layout.addLayoutItem(leg)
label('Xəritə haqqında',325,145,78,7,10,'#1a5276',True,Qt.AlignCenter)
label('• Rayon sərhədləri\n• Seçilmiş turizm obyektləri\n• Şəhər və yaşayış məntəqələri\n• OpenStreetMap əsas xəritəsi\n\nMəqsəd: Quba–Qusar məkanında\nturizm fəaliyyətlərinin aydın\və oxunaqlı göstərilməsi.',326,154,76,54,7.5,'#3b3028',False)
label('Miqyas və istiqamət',325,213,78,7,10,'#1a5276',True,Qt.AlignCenter)
scale=QgsLayoutItemScaleBar(layout); scale.setStyle('Single Box'); scale.setUnits(QgsUnitTypes.DistanceKilometers); scale.setUnitLabel('km'); scale.setNumberOfSegments(4); scale.setNumberOfSegmentsLeft(0); scale.setUnitsPerSegment(10); scale.setLinkedMap(map_item); scale.setFrameEnabled(False); scale.attemptMove(QgsLayoutPoint(327,225,QgsUnitTypes.LayoutMillimeters)); scale.attemptResize(QgsLayoutSize(72,12)); layout.addLayoutItem(scale)
north=QgsLayoutItemPicture(layout); north.setPicturePath('/usr/share/qgis/svg/arrows/NorthArrow_01.svg'); north.attemptMove(QgsLayoutPoint(378,242,QgsUnitTypes.LayoutMillimeters)); north.attemptResize(QgsLayoutSize(20,25)); north.setFrameEnabled(False); layout.addLayoutItem(north)
label('Mənbə: QGIS layihəsi; rayon sərhədləri və turizm inventarı, /tmp/tmd/data/geojson/',10,283,400,6,6.3,'#6a5b50',False,Qt.AlignLeft)

project.layoutManager().addLayout(layout)
project.write(str(QGZ))
exporter=QgsLayoutExporter(layout)
ims=QgsLayoutExporter.ImageExportSettings(); ims.dpi=300; exporter.exportToImage(str(PNG),ims)
pdfs=QgsLayoutExporter.PdfExportSettings(); pdfs.dpi=300; pdfs.forceVectorOutput=True; exporter.exportToPdf(str(PDF),pdfs)
print('QGIS_EXPORT', PNG, PDF, QGZ)
print('LAYERS', [l.name() for l in project.mapLayers().values()])
QgsApplication.exitQgis()
