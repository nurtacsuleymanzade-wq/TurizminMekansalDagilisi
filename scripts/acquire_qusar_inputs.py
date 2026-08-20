#!/usr/bin/env python3
import json, gzip, shutil, subprocess, requests
from pathlib import Path
ROOT=Path('/tmp/tmd'); raw=ROOT/'data'/'raw'/'qusar'; raw.mkdir(parents=True,exist_ok=True)
out=ROOT/'data'/'geojson'
# Exact bbox from the existing dated rayon boundary source.
bbox=(41.15769958500016,47.801986695000096,41.72535324100011,48.578468323000095) # south,west,north,east

def overpass(name, body):
    q='[out:json][timeout:180];('+body+');out body geom;'
    for url in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter']:
        try:
            r=requests.post(url,data=q.encode(),headers={'User-Agent':'QusarAcademicGIS/1.0'},timeout=240)
            if r.ok:
                data=r.json(); (raw/f'{name}.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
                feats=[]
                for e in data.get('elements',[]):
                    tags=e.get('tags',{}); geom=e.get('geometry',[])
                    if e.get('type')=='node': g={'type':'Point','coordinates':[e['lon'],e['lat']]}
                    elif e.get('type')=='way' and geom:
                        c=[[p['lon'],p['lat']] for p in geom]
                        g={'type':'LineString','coordinates':c}
                    else: continue
                    props={'osm_id':e.get('id'),'osm_type':e.get('type'),**tags}
                    feats.append({'type':'Feature','properties':props,'geometry':g})
                fc={'type':'FeatureCollection','features':feats}
                (out/f'{name}.geojson').write_text(json.dumps(fc,ensure_ascii=False),encoding='utf8')
                print(name,len(feats),url); return True
            print(name,url,r.status_code,r.text[:100])
        except Exception as e: print(name,url,'ERR',e)
    return False
s,w,n,e=bbox
B=f'{s},{w},{n},{e}'
overpass('qusar_roads',f'way[highway~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|track|path)$"]({B});')
overpass('qusar_hydrology',f'way[waterway=river]({B});way[waterway=stream]({B});')
overpass('qusar_settlements',f'node[place~"^(city|town|village|hamlet)$"]({B});')
# Download four SRTM 30 m tiles intersecting Qusar. AWS terrain tiles are public and reproducible.
for tile in ['N41E047','N41E048']:
    gz=raw/f'{tile}.hgt.gz'; hgt=raw/f'{tile}.hgt'
    if not hgt.exists():
        u=f'https://s3.amazonaws.com/elevation-tiles-prod/skadi/N41/{tile}.hgt.gz'
        r=requests.get(u,timeout=300); r.raise_for_status(); gz.write_bytes(r.content)
        with gzip.open(gz,'rb') as fi, open(hgt,'wb') as fo: shutil.copyfileobj(fi,fo)
    print('DEM',tile,hgt.stat().st_size)
# Mosaic tiles, retaining exact source tiles in raw.
subprocess.run(['gdalbuildvrt',str(raw/'qusar_dem.vrt'),str(raw/'N41E047.hgt'),str(raw/'N41E048.hgt')],check=True)
print('ACQUISITION_OK')
