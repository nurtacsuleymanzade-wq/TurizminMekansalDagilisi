# Azerbaycan'da Turizm Faaliyetlerinin Mekânsal Dağılışı

Doktora tezi kapsamında Azerbaycan turizm faaliyetlerinin mekânsal ve zamansal desenlerini Coğrafi Bilgi Sistemleri (CBS) ve mekânsal istatistik yöntemleriyle analiz eden interaktif web sitesi.

## 📋 İçindekiler

- [Proje Hakkında](#proje-hakkında)
- [Web Sitesi Bölümleri](#web-sitesi-bölümleri)
- [Kullanılan Teknolojiler](#kullanılan-teknolojiler)
- [Veri Kaynakları](#veri-kaynakları)
- [Klasör Yapısı](#klasör-yapısı)
- [Kurulum](#kurulum)
- [Katkıda Bulunma](#katkıda-bulunma)
- [Lisans](#lisans)

## 🎯 Proje Hakkında

Bu proje, Azerbaycan'da turizm faaliyetlerinin mekânsal dağılışını analiz etmek amacıyla yürütülen doktora tez çalışmasının çıktılarını görselleştirmek ve paylaşmak için oluşturulmuştur.

**Kapsanan analizler:**
- Kernel Density Estimation (KDE)
- Global ve Yerel Moran's I (LISA)
- Getis-Ord Gi* Hot Spot / Cold Spot analizi
- Turizm yoğunluk indeksi ve Location Quotient
- Erişilebilirlik ve servis alanı analizi
- OLS, Spatial Lag/Spatial Error ve GWR regresyon modelleri
- Zamanlar arası turizm gelişim tipolojisi

**Zaman aralığı:** 2005–2025 (2005, 2010, 2015, 2019, 2020, 2022, 2024, 2025)

## 🗺️ Web Sitesi Bölümleri

| Bölüm | Açıklama |
|-------|----------|
| **Ana Sayfa** | Proje özeti, temel göstergeler ve bölüm navigasyonu |
| **Haritalar** | İnteraktif haritalar (turizm noktaları, yoğunluk, erişilebilirlik, tarihî değişim) |
| **Grafikler** | Zamansal trendler, rayon karşılaştırmaları, mevsimsellik, dağılım grafikleri |
| **Analizler** | Mekânsal istatistik sonuçları, regresyon modelleri, yorumlar |
| **Veri** | Veri kaynakları, metodoloji, kayıt defteri ve kalite raporları |

## 🛠️ Kullanılan Teknolojiler

- **Frontend:** HTML5, CSS3, JavaScript (vanilla)
- **Haritalama:** Leaflet.js
- **Grafikler:** Chart.js
- **Harita Taban Haritası:** OpenStreetMap / CartoDB
- **Barındırma:** GitHub Pages
- **Veri İşleme:** Python (pandas, geopandas, pysal, matplotlib, seaborn)

> **Not:** Dinamik içerik (haritalar, grafikler, veri tabloları) mevcut veriler toplandıkça ve analizler tamamlandıkça eklenecektir.

## 📊 Veri Kaynakları

| Kaynak | Tür | Durum |
|--------|-----|-------|
| Azərbaycan Dövlət Statistika Komitəsi | Turizm istatistikleri (resmî) | 📥 Toplanacak |
| Azərbaycan Turizm Bürosu | Aylık turizm raporları | 📥 Toplanacak |
| OpenStreetMap / Overpass API | Turistik POI'ler, yol ağı | 📥 Toplanacak |
| UNESCO World Heritage | Kültürel miras alanları | 📥 Toplanacak |
| Protected Planet | Korunan alanlar | 📥 Toplanacak |
| Ekoloji və Təbii Sərvətlər Nazirliyi | Doğal kaynaklar | 📥 Toplanacak |
| Mədəniyyət Nazirliyi | Kültürel varlık envanteri | 📥 Toplanacak |
| ERA5 / Copernicus Climate Data Store | İklim verileri | 📥 Toplanacak |
| SRTM / Copernicus DEM | Sayısal yükseklik modeli | 📥 Toplanacak |

## 📁 Klasör Yapısı

```
TurizminMekansalDagilisi/
├── index.html              # Ana sayfa
├── harita.html             # İnteraktif haritalar sayfası
├── grafikler.html          # Grafikler ve tablolar sayfası
├── analizler.html          # Mekânsal analiz sonuçları sayfası
├── veri.html               # Veri kaynakları sayfası
├── style.css               # Stil dosyası
├── README.md               # Bu dosya
├── data/
│   ├── raw/                # Ham veriler (orijinal format)
│   ├── processed/          # İşlenmiş / temizlenmiş veriler
│   └── geojson/            # GeoJSON formatında mekânsal veriler
├── assets/
│   └── images/             # Görsel dosyalar (harita PNG, grafik PNG)
├── maps/                   # Harita dosyaları (çıktılar)
├── charts/                 # Grafik dosyaları (çıktılar)
├── scripts/                # Veri toplama ve analiz scriptleri
├── metadata/
│   └── source_registry.csv # Veri kaynak kayıt defteri
└── models/                 # Regresyon model çıktıları
```

## 🚀 Kurulum

Bu proje statik bir web sitesidir. Yerel olarak çalıştırmak için:

```bash
# 1. Repoyu klonlayın
git clone https://github.com/nurtacsuleymanzade-wq/TurizminMekansalDagilisi.git

# 2. Klasöre gidin
cd TurizminMekansalDagilisi

# 3. Basit bir HTTP sunucusu ile çalıştırın
python3 -m http.server 8000

# 4. Tarayıcınızda http://localhost:8000 adresini açın
```

### VPS üzerinde çalıştırma

```bash
# Kalıcı sunucu için
cd /path/to/TurizminMekansalDagilisi
nohup python3 -m http.server 8080 > server.log 2>&1 &
```

## 🤝 Katkıda Bulunma

Bu proje kişisel bir doktora tez çalışmasıdır. Veri setleri, analizler ve görselleştirmeler tez danışmanı kontrolünde ilerlemektedir.

## 📄 Lisans

© 2025 Nurtac Süleymanzade. Tüm hakları saklıdır.

Bu projedeki veriler ve analiz sonuçları akademik çalışma amaçlıdır. Kaynak gösterilmeden kullanılamaz.
