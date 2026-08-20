#!/usr/bin/env python3
"""Prepare a truthful Qusar tourism inventory by spatially clipping the real POI registry.

No coordinates are invented: every output feature is copied from all_pois_enhanced.geojson
and retained only when its geometry intersects the official Qusar rayon boundary.
"""
from pathlib import Path
import json
from shapely.geometry import shape, mapping

ROOT = Path('/tmp/tmd')
BOUNDARY = ROOT/'data/geojson/azerbaijan_rayon_boundaries.geojson'
SOURCE = ROOT/'data/geojson/all_pois_enhanced.geojson'
OUT = ROOT/'data/geojson/qusar_tourism_points.geojson'

boundary_data = json.loads(BOUNDARY.read_text())
q_features = [f for f in boundary_data['features'] if f.get('properties', {}).get('adm1_name1') == 'Qusar']
if len(q_features) != 1:
    raise RuntimeError(f'Expected exactly one Qusar boundary, found {len(q_features)}')
qgeom = shape(q_features[0]['geometry'])
source_data = json.loads(SOURCE.read_text())

# Map the verified source taxonomy to the master map's eight-category schema.
category_map = {
    'Otel/Konaklama': 'Otel',
    'Park-Plaj-Doğa': 'Doga_Alani',
    'Tarihi-Kültürel': 'Tarihi_Anit',
    'Yeme-İçme': 'Diger_Tesis',
}
features = []
for src in source_data['features']:
    geom = shape(src['geometry'])
    if not qgeom.intersects(geom):
        continue
    props = dict(src.get('properties') or {})
    source_category = props.get('category', '')
    master_category = category_map.get(source_category)
    if not master_category:
        raise RuntimeError(f'Unmapped source category: {source_category!r}')
    props.update({
        'category': master_category,
        'source_category': source_category,
        'source_registry': 'all_pois_enhanced.geojson',
        'spatial_rule': 'intersects official Qusar rayon boundary (adm1_name1=Qusar)',
        'verification_status': 'SOURCE_SPATIAL_MATCH',
    })
    features.append({'type': 'Feature', 'geometry': mapping(geom), 'properties': props})

out = {'type': 'FeatureCollection', 'name': 'Qusar tourism points — spatially verified source subset', 'features': features}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print('SOURCE_FEATURES', len(source_data['features']))
print('QUSAR_FEATURES', len(features))
from collections import Counter
print('CATEGORIES', dict(sorted(Counter(f['properties']['category'] for f in features).items())))
print('OUTPUT', OUT)
