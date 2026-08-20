import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pathlib import Path

base=Path('/tmp/tmd')
out=Path('/root/Quba_Qusar_Oxunaqli_Harita.png')
ray0=gpd.read_file(base/'data/geojson/azerbaijan_rayon_boundaries.geojson')
poi0=gpd.read_file(base/'data/geojson/all_pois_enhanced.geojson')
# select in WGS84 before projection
sel0=ray0[ray0['center_lon'].between(47.7,48.7) & ray0['center_lat'].between(40.9,41.7)].copy()
p0=poi0.cx[47.7:48.7,40.9:41.7].copy()
ray=ray0.to_crs(3857); poi=poi0.to_crs(3857)
sel=ray.loc[sel0.index].copy(); p=poi.loc[p0.index].copy()
# use only main categories, cap visually overwhelming restaurant points via deterministic sample
cats=['Yeme-İçme','Otel/Konaklama','Tarihi-Kültürel','Spor','Alışveriş-Eğlence','Park-Plaj-Doğa']
styles={
 'Yeme-İçme':('#d73027','o','Restoran / Kafe'),
 'Otel/Konaklama':('#762a83','D','Otel / Konaklama'),
 'Tarihi-Kültürel':('#2166ac','s','Muzey / Tarixi abidə'),
 'Spor':('#1a9850','^','İdman'),
 'Alışveriş-Eğlence':('#e08214','P','Alış-veriş'),
 'Park-Plaj-Doğa':('#1b9e77','X','Park / Təbiət'),
}
fig,ax=plt.subplots(figsize=(14,10),facecolor='#f5f0e8')
ax.set_facecolor('#fffdf8')
# draw all selected rayon boundaries strongly
colors=['#d9ead3','#fce5cd','#d0e0e3','#eadcf8']
for i,(_,r) in enumerate(sel.iterrows()):
 gpd.GeoSeries([r.geometry],crs=3857).plot(ax=ax,facecolor=colors[i%len(colors)],edgecolor='#4f4a43',linewidth=2.0,alpha=0.75,zorder=1)
 c=r.geometry.representative_point(); ax.text(c.x,c.y,str(r.get('adm1_name1') or r.get('adm1_name')),ha='center',va='center',fontsize=13,fontweight='bold',color='#3c3832',zorder=3)
# points
for cat in cats:
 q=p[p['category'].astype(str)==cat].copy()
 # retain all non-food, sample food to keep map legible
 if cat=='Yeme-İçme' and len(q)>180: q=q.iloc[::max(1,len(q)//180)]
 if len(q)==0: continue
 color,marker,label=styles[cat]
 ax.scatter(q.geometry.x,q.geometry.y,s=38 if cat!='Yeme-İçme' else 25,c=color,marker=marker,edgecolors='white',linewidths=.65,alpha=.92,zorder=5,label=f'{label} ({len(q)})')
# labels for named major landmarks in region
for _,r in p[p['name'].notna()].iterrows():
 n=str(r['name'])
 if any(k in n.lower() for k in ['xınalıq','khinalig','afurca','shahdag','şahdağ','laza','qusar','quba']):
  ax.annotate(n,(r.geometry.x,r.geometry.y),xytext=(4,4),textcoords='offset points',fontsize=8,color='#222',bbox=dict(fc='white',ec='none',alpha=.75,pad=1),zorder=7)
ax.set_title('QUBA–QUSAR RAYONLARI\nTurizm obyektlərinin məkan üzrə paylanması',fontsize=24,fontweight='bold',color='#1a5276',pad=22)
ax.text(.5,1.005,'Azərbaycan | OSM turizm POI-ləri | rayon sərhədləri',transform=ax.transAxes,ha='center',fontsize=12,color='#555')
ax.legend(loc='lower right',frameon=True,facecolor='white',edgecolor='#555',fontsize=11,title='ŞƏRTİ İŞARƏLƏR',title_fontsize=13)
ax.set_axis_off(); ax.set_aspect('equal')
# north arrow
ax.annotate('N',xy=(.96,.90),xycoords='axes fraction',ha='center',fontsize=22,fontweight='bold',color='#1a5276')
ax.annotate('',xy=(.96,.88),xytext=(.96,.80),xycoords='axes fraction',arrowprops=dict(arrowstyle='-|>',lw=3,color='#1a5276'))
fig.text(.02,.02,'Mənbə: OpenStreetMap; Azərbaycan rayon sərhədləri | Hazırlayan: N.T.Süleymanzadə',fontsize=9,color='#555')
plt.tight_layout(); fig.savefig(out,dpi=300,bbox_inches='tight',facecolor=fig.get_facecolor()); print(out, out.stat().st_size, len(sel), len(p))
