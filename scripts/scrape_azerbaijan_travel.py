#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract POI data from azerbaijan.travel trip pages."""
import requests
import re
import json
import time
import os
from collections import Counter

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}
OUTPUT_DIR = '/tmp/TurizminMekansalDagilisi/data/raw'
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# Category keywords
CAT_FOOD = ['restoran', 'restaurant', 'cafe', 'kafe', 'yemek', 'food', 'cuisine', 'culinary',
            'dolma', 'halva', 'sweet', 'dining', 'eat', 'meal', 'sirniyyat', 'sherbet',
            'cook', 'shorba', 'baklava', 'bar']
CAT_HOTEL = ['hotel', 'hostel', 'accommodation', 'otel', 'stay', 'lodge', 'resort',
             'guesthouse', 'qonaq', 'konaklama']
CAT_CULTURAL = ['museum', 'muzey', 'monument', 'historical', 'tarixi', 'medeniyyet',
                'theatre', 'teatr', 'palace', 'saray', 'khan', 'xan', 'caravanserai',
                'karvansaray', 'workshop', 'heritage', 'carpet', 'xalca', 'castle',
                'qala', 'fortress', 'tower', 'ancient', 'cultural', 'art', 'exhibition',
                'serqi', 'memorial', 'abad', 'kelaghai', 'kelaghayi', 'shebeke',
                'sebeke', 'history', 'library', 'kitab', 'medeni', 'silk road',
                'ipek yolu', 'ev muzeyi', 'house museum']
CAT_SPORT = ['sport', 'stadium', 'arena', 'idman', 'golf', 'hiking', 'trekking',
             'bike', 'cycling', 'fitness', 'gym', 'stadyum', 'rafting', 'ski',
             'xizek', 'velosiped', 'climbing', 'dirmanma']
CAT_SHOP = ['mall', 'shopping', 'alis-veris', 'market', 'shop', 'magaza', 'bazaar',
            'bazar', 'pazar', 'entertainment', 'eylence', 'cinema', 'kino', 'club',
            'gece']
CAT_NATURE = ['park', 'beach', 'cimerlik', 'nature', 'tebiet', 'national park',
              'lake', 'gol', 'mountain', 'dag', 'mese', 'forest', 'garden', 'bag',
              'waterfall', 'selale', 'canyon', 'valley', 'dere', 'reserve', 'qoruq',
              'ecotourism', 'eco', 'sahil', 'gezinti', 'walk', 'trail', 'sahil']
CAT_RELIGIOUS = ['mosque', 'mescid', 'church', 'kilse', 'temple', 'mebed',
                 'religious', 'dini', 'monastir', 'monastery', 'cami', 'synagogue',
                 'cathedral', 'prayer', 'turbe', 'tomb', 'shrine', 'mazar']

def categorize_poi(name, desc):
    text = (name + ' ' + desc).lower()
    for kwlist, cat in [(CAT_FOOD, 'Yeme-icme'), (CAT_HOTEL, 'Otel/Konaklama'),
                         (CAT_CULTURAL, 'Tarihi-Kulturel'), (CAT_SPORT, 'Spor'),
                         (CAT_SHOP, 'Alisveris-Eglence'), (CAT_NATURE, 'Park-Plaj-Doga'),
                         (CAT_RELIGIOUS, 'Dini Yerler')]:
        if any(k in text for k in kwlist):
            return cat
    return 'Tarihi-Kulturel'

def extract_pois_from_trip_page(url, region, city_name=None):
    print('  Fetching: ' + url)
    try:
        resp = SESSION.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        print('  ERROR: ' + str(e))
        return []

    html = resp.text
    m = re.search(r'p_json_data\s*=\s*(\{.*?\});', html, re.DOTALL)
    if not m:
        print('  No p_json_data found')
        return []

    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        print('  JSON decode error: ' + str(e))
        return []

    pois = []
    for section_key, section_data in data.items():
        if not isinstance(section_data, dict) or 'items' not in section_data:
            continue
        for item in section_data['items']:
            title = item.get('title', '').strip()
            lat = item.get('lat')
            lng = item.get('lng')
            if not title or not lat or not lng:
                continue
            desc_html = item.get('desc', '')
            desc = re.sub(r'<[^>]+>', ' ', desc_html).strip()
            desc = desc.replace('More', '').strip()
            desc = desc.replace('&nbsp;', ' ').replace('&rsquo;', "'")
            desc = desc.replace('&#39;', "'").replace('&amp;', '&')

            category = categorize_poi(title, desc)
            rayon = city_name if city_name else region

            poi = {
                'name': title,
                'category': category,
                'subcategory': '',
                'source': 'azerbaijan_travel',
                'region': region,
                'rayon': rayon,
                'latitude': float(lat),
                'longitude': float(lng),
                'description': desc[:500] if desc else '',
            }
            pois.append(poi)

    print('  Extracted ' + str(len(pois)) + ' POIs')
    return pois

def extract_region(url):
    m = re.search(r'azerbaijan\.travel/([a-z-]+)', url.lower())
    if m:
        name = m.group(1).replace('-', ' ').title()
        return name
    return 'Unknown'

def main():
    print('=== Extract POI data from azerbaijan.travel ===')

    trip_pages = [
        ('https://azerbaijan.travel/trip-to-guba', 'Quba-Xacmaz', 'Quba'),
        ('https://azerbaijan.travel/trip-to-sheki', 'Seki-Zaqatala', 'Sheki'),
        ('https://azerbaijan.travel/trip-to-baku', 'Baki', 'Baku'),
        ('https://azerbaijan.travel/trip-to-gabala', 'Seki-Zaqatala', 'Gabala'),
        ('https://azerbaijan.travel/trip-to-ganja', 'Gence-Daskesen', 'Ganja'),
        ('https://azerbaijan.travel/trip-to-gakh', 'Seki-Zaqatala', 'Gakh'),
        ('https://azerbaijan.travel/trip-to-gusar', 'Quba-Xacmaz', 'Gusar'),
        ('https://azerbaijan.travel/trip-to-ismayilli', 'Dagliq Sirvan', 'Ismayilli'),
        ('https://azerbaijan.travel/trip-to-lankaran', 'Lenkeran-Astara', 'Lankaran'),
        ('https://azerbaijan.travel/trip-to-shamakhi', 'Dagliq Sirvan', 'Shamakhi'),
        ('https://azerbaijan.travel/trip-to-nakhichevan', 'Naxcivan', 'Nakhchivan'),
        ('https://azerbaijan.travel/trip-to-shamkir', 'Gence-Daskesen', 'Shamkir'),
        ('https://azerbaijan.travel/trip-to-goygol', 'Gence-Daskesen', 'Goygol'),
        ('https://azerbaijan.travel/trip-to-zagatala', 'Seki-Zaqatala', 'Zagatala'),
        ('https://azerbaijan.travel/trip-to-lerik', 'Lenkeran-Astara', 'Lerik'),
        ('https://azerbaijan.travel/trip-to-mingachevir', 'Merkezi Aran', 'Mingachevir'),
        ('https://azerbaijan.travel/trip-to-naftalan', 'Gence-Daskesen', 'Naftalan'),
        ('https://azerbaijan.travel/trip-to-khizi', 'Quba-Xacmaz', 'Khizi'),
        ('https://azerbaijan.travel/trip-to-shusha', 'Qarabag', 'Shusha'),
    ]

    all_pois = []
    for url, region, city_name in trip_pages:
        pois = extract_pois_from_trip_page(url, region, city_name)
        all_pois.extend(pois)
        time.sleep(1.5)

    # Deduplicate
    seen = set()
    unique_pois = []
    for p in all_pois:
        key = (p['name'], round(p['latitude'], 4), round(p['longitude'], 4))
        if key not in seen:
            seen.add(key)
            unique_pois.append(p)

    print()
    print('=== RESULTS ===')
    print('Raw POIs: ' + str(len(all_pois)))
    print('Unique POIs: ' + str(len(unique_pois)))

    output_path = os.path.join(OUTPUT_DIR, 'azerbaijan_travel_pois.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(unique_pois, f, ensure_ascii=False, indent=2)
    print('Saved to ' + output_path)

    cat_counts = Counter(p['category'] for p in unique_pois)
    print()
    print('Category breakdown:')
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print('  ' + cat + ': ' + str(count))

    return unique_pois

if __name__ == '__main__':
    pois = main()
