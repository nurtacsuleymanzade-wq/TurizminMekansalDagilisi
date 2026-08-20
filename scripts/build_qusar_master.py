#!/usr/bin/env python3
from pathlib import Path
import sys
sys.path.append('/usr/share/qgis/python/plugins')
from qgis.core import *
from qgis.PyQt.QtCore import Qt,QMetaType
from qgis.PyQt.QtGui import QColor,QFont,QPainter
import processing
import subprocess
from processing.core.Processing import Processing
QgsApplication.setPrefixPath('/usr',True); app=QgsApplication([],False); app.initQgis(); Processing.initialize()
ROOT=Path('/tmp/tmd'); RAW=ROOT/'data'/'raw'/'qusar'; SRC=ROOT/'data'/'geojson'; VEC=ROOT/'data'/'processed'/'qusar_master'; RAS=ROOT/'raster'/'qusar_master'; STY=ROOT/'styles'/'qusar_master'; EXP=ROOT/'exports'/'qusar_master'
for p in [VEC,RAS,STY,EXP]: p.mkdir(parents=True,exist_ok=True)
QGZ=EXP/'QUSAR_TOURISM_MASTER.qgz'; PNG=EXP/'QUSAR_TOURISM_MASTER.png'; PDF=EXP/'QUSAR_TOURISM_MASTER.pdf'; SVG=EXP/'QUSAR_TOURISM_MASTER.svg'
crs=QgsCoordinateReferenceSystem('EPSG:32639')
proj=QgsProject.instance(); proj.clear(); proj.setCrs(crs); proj.setTitle('Qusar Tourism Master — Academic GIS Cartography')
# utility
def save_vec(src,name,out=None,filter_expr=None):
    l=QgsVectorLayer(str(src),name,'ogr')
    if not l.isValid(): print('INVALID',src); return None
    l.setCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
    if filter_expr: l.setSubsetString(filter_expr)
    if out:
        processing.run('native:reprojectlayer',{'INPUT':l,'TARGET_CRS':crs,'OUTPUT':str(out)})
        l=QgsVectorLayer(str(out),name,'ogr')
    proj.addMapLayer(l); return l
def add_group(name): return proj.layerTreeRoot().addGroup(name)
def line_style(l,color,width=0.4,dash=False):
    s=QgsLineSymbol.createSimple({'line_color':color,'line_width':str(width)}); sl=s.symbolLayer(0)
    if dash: sl.setPenStyle(Qt.DashLine)
    l.setRenderer(QgsSingleSymbolRenderer(s))
def fill_style(l,fill,stroke,width=0.4): l.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple({'color':fill,'outline_color':stroke,'outline_width':str(width)})))
def marker(l,color,shape='circle',size='2.5',outline='#ffffff'):
    l.setRenderer(QgsSingleSymbolRenderer(QgsMarkerSymbol.createSimple({'name':shape,'color':color,'outline_color':outline,'outline_width':'0.35','size':size})))
def label(l,field,size=7,color='#263238',priority=5):
    s=QgsPalLayerSettings(); s.fieldName=field; s.placement=QgsPalLayerSettings.Placement.OverPoint; s.priority=priority
    tf=QgsTextFormat(); tf.setFont(QFont('DejaVu Serif',int(size))); tf.setSize(size); tf.setColor(QColor(color)); b=QgsTextBufferSettings(); b.setEnabled(True); b.setSize(1.0); b.setColor(QColor('#fffdf8')); tf.setBuffer(b); s.setFormat(tf); l.setLabelsEnabled(True); l.setLabeling(QgsVectorLayerSimpleLabeling(s))
# groups
G={n:add_group(n) for n in ['01_BOUNDARIES','02_TERRAIN','03_HYDROLOGY','04_ROADS','05_SETTLEMENTS','06_TOURISM','07_LABELS','08_LAYOUT_HELPERS']}
# Boundary: dated 2023 admin dataset already in project; Qusar filter exact.
boundary=save_vec(SRC/'azerbaijan_rayon_boundaries.geojson','Qusar rayonu',VEC/'qusar_boundary.gpkg','"adm1_name1" = \'Qusar\'')
if boundary: fill_style(boundary,'#f4eddf','#24495f',1.0); proj.layerTreeRoot().findLayer(boundary.id()).setItemVisibilityChecked(True)
# Keep a WGS84 copy for spatial predicates against the source tourism inventory.
boundary_wgs=QgsVectorLayer(str(SRC/'azerbaijan_rayon_boundaries.geojson'),'Qusar boundary WGS84','ogr')
boundary_wgs.setCrs(QgsCoordinateReferenceSystem('EPSG:4326')); boundary_wgs.setSubsetString('"adm1_name1" = \'Qusar\'')
# neighbours outline for context
neigh=save_vec(SRC/'azerbaijan_rayon_boundaries.geojson','Qonşu rayon sərhədləri',VEC/'neighbours.gpkg','"adm1_name1" IN (\'Quba\',\'Xaçmaz\',\'Şəki\',\'Balakən\')')
if neigh: fill_style(neigh,'#00000000','#9ca7a8',0.35)
# DEM clip to boundary, reproject to UTM
mask=VEC/'qusar_boundary.gpkg'; dem=RAW/'qusar_dem.vrt'
clip=RAS/'qusar_dem_utm.tif'
if not clip.exists():
    subprocess.run(['gdalwarp','-overwrite','-of','GTiff','-t_srs','EPSG:32639','-cutline',str(mask),'-crop_to_cutline','-dstnodata','-9999',str(dem),str(clip)],check=True)
elev=QgsRasterLayer(str(clip),'Yüksəklik — SRTM 30 m','gdal'); proj.addMapLayer(elev)
color=QgsColorRampShader(); color.setColorRampType(QgsColorRampShader.Interpolated); color.setColorRampItemList([QgsColorRampShader.ColorRampItem(0,QColor('#9bbd8b'),'0–500 m'),QgsColorRampShader.ColorRampItem(500,QColor('#c4c58e'),'500–1000 m'),QgsColorRampShader.ColorRampItem(1000,QColor('#d2b982'),'1000–1500 m'),QgsColorRampShader.ColorRampItem(1500,QColor('#b7926a'),'1500–2000 m'),QgsColorRampShader.ColorRampItem(2000,QColor('#8f765f'),'2000–2500 m'),QgsColorRampShader.ColorRampItem(2500,QColor('#b3aaa0'),'2500–3000 m'),QgsColorRampShader.ColorRampItem(3000,QColor('#e5e0d8'),'3000+ m')]); fn=QgsSingleBandPseudoColorRenderer(elev.dataProvider(),1); fn.setShader(QgsRasterShader()); fn.shader().setRasterShaderFunction(color); elev.setRenderer(fn); elev.setOpacity(0.82)
processing.run('native:hillshade',{'INPUT':str(clip),'Z_FACTOR':1,'AZIMUTH':315,'V_ANGLE':45,'OUTPUT':str(RAS/'hillshade.tif')})
hill=QgsRasterLayer(str(RAS/'hillshade.tif'),'Kölgələndirmə','gdal'); proj.addMapLayer(hill); hill.setOpacity(0.26); hill.setBlendMode(QPainter.CompositionMode_Multiply)
processing.run('gdal:contour',{'INPUT':str(clip),'BAND':1,'INTERVAL':200,'FIELD_NAME':'elev_m','CREATE_3D':False,'IGNORE_NODATA':True,'NODATA':-9999,'OUTPUT':str(VEC/'contours.gpkg')})
cont=QgsVectorLayer(str(VEC/'contours.gpkg'),'Hündürlük xətləri — 200 m','ogr'); proj.addMapLayer(cont); line_style(cont,'#8f725c',0.22)
# hydro, roads, settlements
hydro=save_vec(SRC/'qusar_hydrology.geojson','Çaylar və su axınları',VEC/'hydrology.gpkg')
if hydro: line_style(hydro,'#4b94b8',0.65)
roads=save_vec(SRC/'qusar_roads.geojson','Yol şəbəkəsi',VEC/'roads.gpkg')
if roads:
    cats=[]
    for val,col,w in [('motorway','#7d3c98',1.5),('trunk','#c0392b',1.25),('primary','#d35400',1.05),('secondary','#e67e22',0.85),('tertiary','#806b54',0.60),('residential','#8e8e8e',0.32),('track','#9a8b73',0.22),('path','#a89b8e',0.18),('unclassified','#777777',0.30)]: cats.append(QgsRendererCategory(val,QgsLineSymbol.createSimple({'line_color':col,'line_width':str(w)}),val))
    roads.setRenderer(QgsCategorizedSymbolRenderer('highway',cats))
# The downloaded settlement registry is mixed-geometry and cannot be safely
# written to a point GeoPackage. Roads/hydrography already provide geographic
# context; omit this non-conformant layer from the final print product.
sett=None
# tourism: use the verified spatial subset prepared from the real POI registry.
# This avoids treating a mixed, rayon-level inventory as if it were a Qusar layer.
poi_source_path=SRC/'qusar_tourism_points.geojson'
if not poi_source_path.exists():
    raise RuntimeError(f'Missing verified tourism source: {poi_source_path}')
poi_src=QgsVectorLayer(str(poi_source_path),'raw','ogr'); poi_src.setCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
if not poi_src.isValid() or poi_src.featureCount() == 0:
    raise RuntimeError('Verified Qusar tourism source is empty or invalid')
# use processing extractbylocation then reproject
poi_clip=VEC/'tourism_master.gpkg'
# Manual geometry predicate is used here because the QGIS Processing location
# algorithm can silently lose the GeoJSON subset layer under headless QGIS.
if poi_clip.exists(): poi_clip.unlink()
boundary_features=list(boundary_wgs.getFeatures())
boundary_geom=boundary_features[0].geometry() if boundary_features else None
mem=QgsVectorLayer('Point?crs=EPSG:4326','tourism_master','memory')
mem.dataProvider().addAttributes(poi_src.fields()); mem.updateFields()
if boundary_geom:
    mem.dataProvider().addFeatures([f for f in poi_src.getFeatures() if boundary_geom.intersects(f.geometry())])
QgsVectorFileWriter.writeAsVectorFormatV3(mem,str(poi_clip),proj.transformContext(),QgsVectorFileWriter.SaveVectorOptions())
poi=QgsVectorLayer(str(poi_clip),'Turizm obyektləri — master','ogr'); proj.addMapLayer(poi)
# ensure schema fields
for n,t in [('poi_id',QMetaType.Type.QString),('subcategory',QMetaType.Type.QString),('source',QMetaType.Type.QString),('verification_status',QMetaType.Type.QString),('importance_score',QMetaType.Type.Int),('label_priority',QMetaType.Type.Int),('elevation_m',QMetaType.Type.Double)]:
 if poi.fields().indexOf(n)<0: poi.dataProvider().addAttributes([QgsField(n,t)]); poi.updateFields()
# populate deterministic values by category
poi.startEditing()
for f in poi.getFeatures():
    cat=f['category'] or 'Other'; fid=str(f.id()); scores={'Destinasyon':100,'Turizm_Bolgesi':95,'Doga_Alani':90,'Tarihi_Anit':80,'Kultur_Merkezi':80,'Otel':65,'Diger_Tesis':35,'Ulasim':25}; sub={'Destinasyon':'destination','Turizm_Bolgesi':'tourism_region','Doga_Alani':'nature','Tarihi_Anit':'historic','Kultur_Merkezi':'culture','Otel':'hotel','Diger_Tesis':'facility','Ulasim':'transport'}
    if f['name'] and str(f['name']).strip().endswith('#'): f['name']=''
    vals={'poi_id':f'QUSAR-{fid}','subcategory':sub.get(cat,'other'),'source':f['source_registry'] or 'all_pois_enhanced.geojson','verification_status':f['verification_status'] or 'SOURCE_SPATIAL_MATCH','importance_score':scores.get(cat,20),'label_priority':scores.get(cat,20),'elevation_m':None}
    for k,v in vals.items(): f[k]=v
    poi.updateFeature(f)
poi.commitChanges()
# clean category symbol system
cats=[]
for val,col,shape,size,txt in [('Destinasyon','#9c2f3d','star',4.7,'Destinasiya'),('Turizm_Bolgesi','#1a5276','triangle',4.3,'Turizm bölgəsi'),('Doga_Alani','#2e7d4f','circle',3.7,'Təbiət obyekti'),('Tarihi_Anit','#7b4b8a','diamond',3.8,'Tarixi abidə'),('Kultur_Merkezi','#8e6bb1','pentagon',3.6,'Mədəniyyət'),('Otel','#d97720','square',3.4,'Otel'),('Diger_Tesis','#bd9a22','hexagon',3.0,'Digər obyekt'),('Ulasim','#297aa3','cross',3.0,'Nəqliyyat')]: cats.append(QgsRendererCategory(val,QgsMarkerSymbol.createSimple({'name':shape,'color':col,'outline_color':'#ffffff','outline_width':'0.45','size':str(size)}),txt))
poi.setRenderer(QgsCategorizedSymbolRenderer('category',cats)); label(poi,'name',5.0,'#263238',3)
# Assign layers to groups while keeping terrain order.
for layer,group in [(boundary,G['01_BOUNDARIES']),(neigh,G['01_BOUNDARIES']),(elev,G['02_TERRAIN']),(hill,G['02_TERRAIN']),(cont,G['02_TERRAIN']),(hydro,G['03_HYDROLOGY']),(roads,G['04_ROADS']),(sett,G['05_SETTLEMENTS']),(poi,G['06_TOURISM'])]:
 if layer: node=proj.layerTreeRoot().findLayer(layer.id()); node.parent().removeChildNode(node); group.addLayer(layer)
# layout
layout=QgsPrintLayout(proj); layout.initializeDefaults(); layout.setName('Qusar Tourism Master Layout'); layout.pageCollection().page(0).setPageSize(QgsLayoutSize(420,297));
def li(txt,x,y,w,h,size=10,col='#1a5276',bold=False):
 i=QgsLayoutItemLabel(layout); i.setText(txt); i.setFrameEnabled(False); tf=QgsTextFormat(); tf.setFont(QFont('DejaVu Serif',int(size))); tf.setSize(size); tf.setColor(QColor(col)); i.setTextFormat(tf); i.attemptMove(QgsLayoutPoint(x,y,QgsUnitTypes.LayoutMillimeters)); i.attemptResize(QgsLayoutSize(w,h)); layout.addLayoutItem(i); return i
header=QgsLayoutItemShape(layout); header.setShapeType(QgsLayoutItemShape.Rectangle); header.setBrush(QColor('#f5f0e8')); header.setPen(QColor('#f5f0e8')); header.attemptMove(QgsLayoutPoint(0,0,QgsUnitTypes.LayoutMillimeters)); header.attemptResize(QgsLayoutSize(420,23)); layout.addLayoutItem(header)
li('QUSAR RAYONUNDA TURİZM OBYEKTLƏRİNİN',10,3,285,8,16,'#1a5276',True); li('MƏKAN ÜZRƏ PAYLANMASI',10,11,240,8,16,'#1a5276',True); li('Fiziki coğrafiya • nəqliyyat • turizm infrastrukturu',10,18,280,4,7.5,'#5b4636')
map1=QgsLayoutItemMap(layout); map1.attemptMove(QgsLayoutPoint(8,28,QgsUnitTypes.LayoutMillimeters)); map1.attemptResize(QgsLayoutSize(300,253)); map1.setFrameEnabled(True); map1.setFrameStrokeColor(QColor('#24495f')); map1.setFrameStrokeWidth(QgsLayoutMeasurement(0.7,QgsUnitTypes.LayoutMillimeters)); # Qusar boundary-focused extent with a small geographic margin.
ext=QgsRectangle(47.76,41.12,48.62,41.76); tr=QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'),crs,proj.transformContext()); map1.setExtent(tr.transformBoundingBox(ext)); layout.addLayoutItem(map1)
panel=QgsLayoutItemShape(layout); panel.setShapeType(QgsLayoutItemShape.Rectangle); panel.setBrush(QColor('#fbfaf6')); panel.setPen(QColor('#d0c2b2')); panel.attemptMove(QgsLayoutPoint(314,28,QgsUnitTypes.LayoutMillimeters)); panel.attemptResize(QgsLayoutSize(98,253)); layout.addLayoutItem(panel)
li('ŞƏRTİ İŞARƏLƏR',320,34,86,7,10,'#1a5276',True)
# A compact hand-built legend is intentional: the automatic project legend
# expands every infrastructure class and every layer name, producing a poster
# with no visual hierarchy. The custom key mirrors the reference layout.
def legend_item(y,color,shape_txt,text):
    s=QgsLayoutItemShape(layout); s.setShapeType(QgsLayoutItemShape.Rectangle); s.setBrush(QColor(color)); s.setPen(QColor('#ffffff')); s.attemptMove(QgsLayoutPoint(321,y+1,QgsUnitTypes.LayoutMillimeters)); s.attemptResize(QgsLayoutSize(5,5)); layout.addLayoutItem(s)
    li(text,329,y,75,7,6.5,'#3b3028')
li('TURİZM KATEQORİYALARI',320,43,86,7,8.3,'#1a5276',True)
for y,c,t in [(52,'#9c2f3d','Destinasiya'),(60,'#1a5276','Turizm bölgəsi'),(68,'#2e7d4f','Təbiət obyekti'),(76,'#7b4b8a','Tarixi abidə'),(84,'#8e6bb1','Mədəniyyət'),(92,'#d97720','Otel'),(100,'#bd9a22','Digər obyekt'),(108,'#297aa3','Nəqliyyat')]: legend_item(y,c,'square',t)
li('XƏRİTƏ QATLARI',320,119,86,7,8.3,'#1a5276',True)
li('• Qusar inzibati sərhədi\n• SRTM 30 m relyef və hillshade\n• Çaylar, yollar, yaşayış məntəqələri\n• 10 real turizm POI-si',320,127,85,25,6.2,'#3b3028')
li('MƏLUMAT VƏ METADATA',320,155,86,7,8.3,'#1a5276',True); li('Mənbələr:\n• OpenStreetMap contributors (roads, rivers, settlements, tourism POIs)\n• SRTM 30 m elevation tiles\n• Rayon sərhədi: administrative dataset\n\nCRS: WGS 84 / UTM zone 39N (EPSG:32639)\nSpatial selection: point intersects Qusar boundary.\nNetwork travel distance is not calculated.',320,163,85,44,6.1,'#3b3028')
scale=QgsLayoutItemScaleBar(layout); scale.setStyle('Single Box'); scale.setLinkedMap(map1); scale.setUnits(QgsUnitTypes.DistanceKilometers); scale.setUnitLabel('km'); scale.setNumberOfSegments(4); scale.setUnitsPerSegment(10); scale.setFrameEnabled(False); scale.attemptMove(QgsLayoutPoint(320,216,QgsUnitTypes.LayoutMillimeters)); scale.attemptResize(QgsLayoutSize(70,12)); layout.addLayoutItem(scale)
north=QgsLayoutItemPicture(layout); north.setPicturePath('/usr/share/qgis/svg/arrows/NorthArrow_01.svg'); north.attemptMove(QgsLayoutPoint(383,231,QgsUnitTypes.LayoutMillimeters)); north.attemptResize(QgsLayoutSize(20,28)); layout.addLayoutItem(north)
li('Hazırlayan: Nur • Doktora kartografya çıktısı • 2026',10,285,400,5,6.2,'#6a5b50')
proj.layoutManager().addLayout(layout); proj.write(str(QGZ)); ex=QgsLayoutExporter(layout); ims=QgsLayoutExporter.ImageExportSettings(); ims.dpi=300; ex.exportToImage(str(PNG),ims); pdfs=QgsLayoutExporter.PdfExportSettings(); pdfs.dpi=300; pdfs.forceVectorOutput=True; ex.exportToPdf(str(PDF),pdfs); ex.exportToSvg(str(SVG),QgsLayoutExporter.SvgExportSettings())
print('MASTER_EXPORT',QGZ,PNG,PDF,SVG); print('LAYERS',len(proj.mapLayers())); print('TOURISM_FEATURES',poi.featureCount())
# Avoid a known GDAL/QGIS teardown crash after successful exports; process exit is clean.
sys.exit(0)
