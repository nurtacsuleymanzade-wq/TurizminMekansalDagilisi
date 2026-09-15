# Nova Atlas public web bundle

Bu dizindeki etkileşimli `harita.html`, `/opt/az-tourism-gis` master GIS projesinin GitHub Pages için hazırlanmış salt-okunur kartografik türevini kullanır.

## Kapsam

- 79 idari birim sınırı
- 142 Atlas Core POI; ülke görünümünde 56 kartografik seçki
- doğal, tarihî-kültürel, konaklama ve yeme-içme envanter katmanları
- 9 doğrulanmış havalimanı, 35 yolcu istasyonu ve 24 doğrulanmış avtovağzal
- ana/ikincil karayolları ve kullanıcı tarafından ayrı açılan 149.351 yan yol geometrisi
- yolcu demiryolu, ana hidrografya, korunan alanlar ve DEM tabanlı rölyef türevi

## Yayın ve gizlilik sınırı

Yayın paketi `scripts/build_public_atlas_bundle.py` ile üretilir. Google Places kimlikleri, Google Maps bağlantıları, kontrol tarihleri, yakın hizmet sorgu yükleri, API anahtarları, VPS secret dosyaları ve master veritabanı bu pakete alınmaz. Google/OSM web sonuçları akademik birincil kaynak statüsünde sunulmaz.

## Etkileşim mantığı

Ülke görünümünde Atlas Core ve ana erişim ağları gösterilir. Yakınlaştırıldığında ayrıntılı POI envanteri açılır. Tertiary, yerel, servis, iz ve patika sınıflarından türetilen “Yan yollar” performans ve okunabilirlik için varsayılan kapalıdır; kontrol panelinden açılıp kapatılır.
