#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract POI data from Google My Maps KML export."""
import xml.etree.ElementTree as ET
import json
import os
import re
from collections import Counter

KML_PATH = '/tmp/TurizminMekansalDagilisi/data/raw/google_mymaps.kml'
OUTPUT_DIR = '/tmp/TurizminMekansalDagilisi/data/geojson'

def parse_kml(kml_path):
    """Parse KML and extract Placemarks with coordinates, names, descriptions."""
    tree = ET.parse(kml_path)
    root = tree.getroot()
    
    # Define namespace
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    placemarks = []
    folders = root.findall('.//kml:Folder', ns)
    folder_names = {}
    
    for folder in folders:
        folder_name_el = folder.find('kml:name', ns)
        fname = folder_name_el.text.strip() if folder_name_el is not None and folder_name_el.text else 'Unknown'
        
        for pm in folder.findall('kml:Placemark', ns):
            name_el = pm.find('kml:name', ns)
            desc_el = pm.find('kml:description', ns)
            point = pm.find('.//kml:Point', ns)
            coords_el = point.find('kml:coordinates', ns) if point is not None else None
            
            name = name_el.text.strip() if name_el is not None and name_el.text else ''
            desc = ''
            if desc_el is not None and desc_el.text:
                # Clean HTML from description
                desc = re.sub(r'<[^>]+>', ' ', desc_el.text).strip()
                desc = re.sub(r'\s+', ' ', desc)
            
            coords = ''
            if coords_el is not None and coords_el.text:
                coords = coords_el.text.strip()
            
            if name and coords:
                parts = coords.split(',')
                if len(parts) >= 2:
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                        placemarks.append({
                            'name': name,
                            'latitude': lat,
                            'longitude': lon,
                            'description': desc[:500] if desc else '',
                            'folder': fname,
                        })
                    except ValueError:
                        pass
    
    return placemarks

# Category keywords (same as before)
CAT_FOOD = ['restoran', 'restaurant', 'cafe', 'kafe', 'yemek', 'food', 'cuisine', 'culinary',
            'dolma', 'halva', 'sweet', 'dining', 'eat', 'meal', 'sirniyyat', 'sherbet',
            'cook', 'shorba', 'baklava', 'bar', 'cay evi', 'çay', 'yemek']
CAT_HOTEL = ['hotel', 'hostel', 'accommodation', 'otel', 'stay', 'lodge', 'resort',
             'guesthouse', 'qonaq', 'konaklama']
CAT_CULTURAL = ['museum', 'muzey', 'monument', 'historical', 'tarixi', 'medeniyyet',
                'theatre', 'teatr', 'palace', 'saray', 'khan', 'xan', 'caravanserai',
                'karvansaray', 'workshop', 'heritage', 'carpet', 'xalca', 'castle',
                'qala', 'fortress', 'tower', 'ancient', 'cultural', 'art', 'exhibition',
                'memorial', 'abad', 'kelaghai', 'kelaghayi', 'shebeke',
                'history', 'library', 'kitab', 'medeni', 'silk road',
                'ev muzeyi', 'house museum', 'yasil', 'yasayis', 'yasayış']
CAT_SPORT = ['sport', 'stadium', 'arena', 'idman', 'golf', 'hiking', 'trekking',
             'bike', 'cycling', 'fitness', 'gym', 'stadyum', 'rafting', 'ski',
             'velosiped', 'climbing']
CAT_SHOP = ['mall', 'shopping', 'alis-veris', 'market', 'shop', 'magaza', 'bazaar',
            'bazar', 'pazar', 'entertainment', 'eylence', 'cinema', 'kino', 'club',
            'gece', 'eglence', 'əyləncə']
CAT_NATURE = ['park', 'beach', 'cimerlik', 'nature', 'tebiet', 'national park',
              'lake', 'gol', 'mountain', 'dag', 'mese', 'forest', 'garden', 'bag',
              'waterfall', 'selale', 'canyon', 'valley', 'dere', 'reserve', 'qoruq',
              'ecotourism', 'eco', 'sahil', 'walk', 'trail', 'cimərlik', 'təbiət',
              'göl', 'dağ', 'meşə', 'bağ', 'şəlalə', 'dərə']
CAT_RELIGIOUS = ['mosque', 'mescid', 'church', 'kilse', 'temple', 'mebed',
                 'religious', 'dini', 'monastir', 'monastery', 'cami', 'synagogue',
                 'cathedral', 'prayer', 'turbe', 'tomb', 'shrine', 'mazar', 'məscid',
                 'kilsə', 'məbəd', 'cami', 'türbə']

def categorize_poi(name, desc, folder=''):
    text = (name + ' ' + desc + ' ' + folder).lower()
    for kwlist, cat in [(CAT_FOOD, 'Yeme-İçme'), (CAT_HOTEL, 'Otel/Konaklama'),
                         (CAT_CULTURAL, 'Tarihi-Kültürel'), (CAT_SPORT, 'Spor'),
                         (CAT_SHOP, 'Alışveriş-Eğlence'), (CAT_NATURE, 'Park-Plaj-Doğa'),
                         (CAT_RELIGIOUS, 'Dini Yerler')]:
        if any(k in text for k in kwlist):
            return cat
    return 'Tarihi-Kültürel'

def main():
    print('=== Extract Google My Maps POIs ===')
    
    if not os.path.exists(KML_PATH):
        print('KML file not found at ' + KML_PATH)
        return []
    
    placemarks = parse_kml(KML_PATH)
    print('Raw Placemarks: ' + str(len(placemarks)))
    
    # Categorize
    pois = []
    for pm in placemarks:
        cat = categorize_poi(pm['name'], pm['description'], pm['folder'])
        
        # Try to infer region/rayon from folder name or description
        region = 'Unknown'
        rayon = 'Unknown'
        
        # Folder-based categorization for some known folders
        fname = pm['folder'].lower()
        if 'baku' in fname or 'baki' in fname:
            rayon = 'Baku'
            region = 'Bakı'
        elif 'quba' in fname or 'qusar' in fname or 'xacmaz' in fname:
            rayon = pm['folder'].split('-')[0].strip() if '-' in pm['folder'] else pm['folder']
            region = 'Quba-Xacmaz'
        elif 'seki' in fname or 'sek' in fname:
            rayon = 'Sheki'
            region = 'Şeki-Zaqatala'
        elif 'qarabag' in fname or 'susa' in fname or 'shusha' in fname:
            rayon = 'Shusha'
            region = 'Qarabağ'
        elif 'gence' in fname or 'goygol' in fname or 'naftalan' in fname:
            rayon = pm['folder'].split('-')[0].strip() if '-' in pm['folder'] else 'Ganja'
            region = 'Gəncə-Daşkəsən'
        elif 'lenkeran' in fname or 'lankaran' in fname or 'astara' in fname:
            rayon = pm['folder'].split('-')[0].strip() if '-' in pm['folder'] else 'Lankaran'
            region = 'Lənkəran-Astara'
        
        poi = {
            'name': pm['name'],
            'category': cat,
            'subcategory': '',
            'source': 'google_mymaps',
            'region': region,
            'rayon': rayon,
            'latitude': pm['latitude'],
            'longitude': pm['longitude'],
            'description': pm['description'],
            'folder': pm['folder'],
        }
        pois.append(poi)
    
    # Deduplicate
    seen = set()
    unique_pois = []
    for p in pois:
        key = (p['name'], round(p['latitude'], 3), round(p['longitude'], 3))
        if key not in seen:
            seen.add(key)
            unique_pois.append(p)
    
    print('Unique POIs: ' + str(len(unique_pois)))
    
    # Save as GeoJSON
    features = []
    for p in unique_pois:
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [p['longitude'], p['latitude']]
            },
            'properties': {
                'Name': p['name'],
                'category': p['category'],
                'subcategory': p['subcategory'],
                'source': p['source'],
                'region': p['region'],
                'rayon': p['rayon'],
                'description': p['description'],
            }
        }
        features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features,
        'metadata': {
            'source': 'Google My Maps - Bütov Azerbaycan',
            'count': len(features)
        }
    }
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, 'google_mymaps_pois.geojson')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)
    print('Saved to ' + output_path)
    
    cat_counts = Counter(p['category'] for p in unique_pois)
    print()
    print('Category breakdown:')
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print('  ' + cat + ': ' + str(count))
    
    # Folder breakdown
    folder_counts = Counter(p['folder'] for p in unique_pois)
    print()
    print('Folder breakdown:')
    for f, count in sorted(folder_counts.items(), key=lambda x: -x[1]):
        print('  ' + f + ': ' + str(count))
    
    return unique_pois

if __name__ == '__main__':
    pois = main()
