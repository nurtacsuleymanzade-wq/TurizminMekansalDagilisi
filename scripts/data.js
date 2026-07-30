// ============================================================
// Azerbaycan Turizm POI Verileri — Örnek/Sample Data
// Turizmin Mekansal Dağılışı (TMD)
// ============================================================
// Kategorize edilmiş turizm noktaları. Gerçek GeoJSON verileri
// hazır olduğunda, bu dosyadaki sabit diziler yerine
// fetch() ile yüklenen GeoJSON FeatureCollection'lar kullanılabilir.
// ============================================================

// Yardımcı: marker renkleri (Leaflet divIcon için)
const MARKER_COLORS = {
    konaklama: '#3b82f6',    // Mavi - Accommodation
    tarihi:    '#8B4513',    // Kahverengi - Historical
    yemeicme:  '#f59e0b',    // Turuncu - Food & Drink
    doga:      '#22c55e',    // Yeşil - Nature
    kultur:    '#8b5cf6',    // Mor - Culture
    ulasim:    '#6b7280',    // Gri - Transportation
    turizm:    '#ef4444'     // Kırmızı - Tourism Regions
};

// ============================================================
// 1. KONAKLAMA (Accommodation) - Mavi
// ============================================================
const konaklamaPOI = [
    { name: 'Hilton Baku', lat: 40.3686, lng: 49.8307, category: 'Otel', source: 'OSM' },
    { name: 'Four Seasons Baku', lat: 40.3661, lng: 49.8328, category: 'Otel', source: 'OSM' },
    { name: 'Fairmont Baku Flame Towers', lat: 40.3596, lng: 49.8268, category: 'Otel', source: 'OSM' },
    { name: 'JW Marriott Absheron', lat: 40.3766, lng: 49.8461, category: 'Otel', source: 'OSM' },
    { name: 'Intourist Hotel Baku', lat: 40.3711, lng: 49.8421, category: 'Otel', source: 'OSM' },
    { name: 'Ramada Ganja Hotel', lat: 40.6832, lng: 46.3667, category: 'Otel', source: 'OSM' },
    { name: 'Sheki Saray Hotel', lat: 41.1975, lng: 47.1620, category: 'Otel', source: 'OSM' },
    { name: 'Gabala Martyrs Hotel', lat: 40.9850, lng: 47.8450, category: 'Tatil Köyü', source: 'OSM' },
    { name: 'Lankaran Springs Wellness', lat: 38.7500, lng: 48.8480, category: 'Termal Otel', source: 'OSM' },
    { name: 'Tebriz Hotel Nakhchivan', lat: 39.2100, lng: 45.4150, category: 'Otel', source: 'OSM' },
    { name: 'Shahdag Hotel', lat: 41.2850, lng: 48.0820, category: 'Kayak Oteli', source: 'OSM' },
    { name: 'Quba Palace Hotel', lat: 41.3615, lng: 48.5100, category: 'Otel', source: 'OSM' },
    { name: 'Khinalig Guesthouse', lat: 41.1768, lng: 48.1280, category: 'Guest House', source: 'OSM' },
    { name: 'Goygol Hotel', lat: 40.5800, lng: 46.3200, category: 'Otel', source: 'OSM' },
    { name: 'Mingachevir Hotel', lat: 40.7710, lng: 47.0490, category: 'Otel', source: 'OSM' },
    { name: 'Shamakhi Palace', lat: 40.6280, lng: 48.6450, category: 'Otel', source: 'OSM' },
    { name: 'ASTARA Otel', lat: 38.4565, lng: 48.8790, category: 'Otel', source: 'OSM' },
    { name: 'Hostel Baku Inn', lat: 40.3740, lng: 49.8400, category: 'Hostel', source: 'OSM' },
    { name: 'Guba Hostel', lat: 41.3600, lng: 48.5060, category: 'Hostel', source: 'OSM' },
    { name: 'Qakh Resort', lat: 41.4185, lng: 46.9200, category: 'Tatil Köyü', source: 'OSM' },
    { name: 'Zagatala Premium Hotel', lat: 41.6330, lng: 46.6450, category: 'Otel', source: 'OSM' },
    { name: 'Sumgait Central Hotel', lat: 40.5880, lng: 49.6320, category: 'Otel', source: 'OSM' },
    { name: 'Shusha Hotel', lat: 39.7600, lng: 46.7500, category: 'Otel', source: 'OSM' },
    { name: 'Gobustan Camp', lat: 40.5350, lng: 48.9350, category: 'Kamp', source: 'OSM' },
    { name: 'Ismayilli Eco Resort', lat: 40.7870, lng: 48.1500, category: 'Eko Otel', source: 'OSM' }
];

// ============================================================
// 2. TARİHİ YERLER (Historical Places) - Kahverengi
// ============================================================
const tarihiPOI = [
    { name: 'Kız Kulesi (Maiden Tower)', lat: 40.3667, lng: 49.8372, category: 'UNESCO Mirası', source: 'UNESCO' },
    { name: 'İçerişehir (Old City)', lat: 40.3663, lng: 49.8364, category: 'UNESCO Mirası', source: 'UNESCO' },
    { name: 'Şirvanşahlar Sarayı', lat: 40.3661, lng: 49.8350, category: 'UNESCO Mirası', source: 'UNESCO' },
    { name: 'Gobustan Kaya Sanatı', lat: 40.1056, lng: 49.3889, category: 'UNESCO Mirası', source: 'UNESCO' },
    { name: 'Şeki Han Sarayı', lat: 41.2047, lng: 47.1922, category: 'UNESCO Mirası', source: 'UNESCO' },
    { name: 'Ateshgah Ateşgedesi', lat: 40.4150, lng: 49.9411, category: 'Tarihi Anıt', source: 'OSM' },
    { name: 'Yanar Dağ (Burning Mountain)', lat: 40.5028, lng: 49.8911, category: 'Doğal Anıt', source: 'OSM' },
    { name: 'Nizami Heykeli (Ganja)', lat: 40.6833, lng: 46.3600, category: 'Anıt', source: 'OSM' },
    { name: 'Cuma Camii (Şamahı)', lat: 40.6278, lng: 48.6400, category: 'Cami', source: 'OSM' },
    { name: 'Mömine Hatun Türbesi', lat: 39.2100, lng: 45.4120, category: 'Türbe', source: 'OSM' },
    { name: 'Baku Bulvarı Sahil', lat: 40.3700, lng: 49.8520, category: 'Tarihi Alan', source: 'OSM' },
    { name: 'Khinalug Antik Köyü', lat: 41.1764, lng: 48.1269, category: 'Tarihi Köy', source: 'OSM' },
    { name: 'Çırag Gala Kalesi', lat: 41.3000, lng: 48.3000, category: 'Kale', source: 'OSM' },
    { name: 'Baku Modern Sanat Müzesi', lat: 40.3770, lng: 49.8560, category: 'Müze', source: 'OSM' },
    { name: 'Azerbaycan Halı Müzesi', lat: 40.3690, lng: 49.8455, category: 'Müze', source: 'OSM' },
    { name: 'Ganja Tarih Müzesi', lat: 40.6830, lng: 46.3580, category: 'Müze', source: 'OSM' },
    { name: 'Şeki Kervansaray', lat: 41.2040, lng: 47.1900, category: 'Kervansaray', source: 'OSM' },
    { name: 'Nakhchivan Han Sarayı', lat: 39.2090, lng: 45.4100, category: 'Saray', source: 'OSM' },
    { name: 'Gülistan Kalesi', lat: 40.6250, lng: 48.6370, category: 'Kale', source: 'OSM' },
    { name: 'Yedi Göbek Mozolesi', lat: 40.7700, lng: 47.0500, category: 'Mozole', source: 'OSM' },
    { name: 'Petroglif Müzesi (Gobustan)', lat: 40.1070, lng: 49.3900, category: 'Müze', source: 'OSM' },
    { name: 'Quba Soykırım Anıtı', lat: 41.3610, lng: 48.5040, category: 'Anıt', source: 'OSM' },
    { name: 'Bibi-Heybet Camii', lat: 40.3100, lng: 49.8850, category: 'Cami', source: 'OSM' },
    { name: 'Nizami Müzesi (Baku)', lat: 40.3790, lng: 49.8490, category: 'Müze', source: 'OSM' },
    { name: 'İçerişehir Hamamı', lat: 40.3655, lng: 49.8370, category: 'Tarihi Hamam', source: 'OSM' }
];

// ============================================================
// 3. YEME-İÇME (Food & Drink) - Turuncu
// ============================================================
const yemeicmePOI = [
    { name: 'Art Club Restaurant', lat: 40.3770, lng: 49.8360, category: 'Restoran', source: 'OSM' },
    { name: 'Firuze Restaurant Baku', lat: 40.3665, lng: 49.8360, category: 'Restoran', source: 'OSM' },
    { name: 'Nakhchivan Restaurant Baku', lat: 40.3715, lng: 49.8440, category: 'Restoran', source: 'OSM' },
    { name: 'Sumakh Restaurant', lat: 40.3690, lng: 49.8310, category: 'Restoran', source: 'OSM' },
    { name: 'Sehrli Tandir Ganja', lat: 40.6835, lng: 46.3620, category: 'Restoran', source: 'OSM' },
    { name: 'Sheki Yapıncı Restaurant', lat: 41.1980, lng: 47.1585, category: 'Restoran', source: 'OSM' },
    { name: 'Gabala Garden Restaurant', lat: 40.9855, lng: 47.8470, category: 'Restoran', source: 'OSM' },
    { name: 'Lankaran Kébap House', lat: 38.7535, lng: 48.8520, category: 'Restoran', source: 'OSM' },
    { name: 'Xinaliq Dağ Evi', lat: 41.1770, lng: 48.1275, category: 'Restoran', source: 'OSM' },
    { name: 'Naxçıvan Saray Restaurant', lat: 39.2105, lng: 45.4140, category: 'Restoran', source: 'OSM' },
    { name: 'Quba Çay Evi', lat: 41.3620, lng: 48.5070, category: 'Kafe', source: 'OSM' },
    { name: 'Cafe City Baku', lat: 40.3760, lng: 49.8500, category: 'Kafe', source: 'OSM' },
    { name: 'Shamakhi Şarap Evi', lat: 40.6290, lng: 48.6430, category: 'Şarap Evi', source: 'OSM' },
    { name: 'Qakh Dağ Restoranı', lat: 41.4190, lng: 46.9210, category: 'Restoran', source: 'OSM' },
    { name: 'Mingachevir Balıq Evi', lat: 40.7715, lng: 47.0505, category: 'Restoran', source: 'OSM' },
    { name: 'Sumgait Sahil Kafe', lat: 40.5840, lng: 49.6350, category: 'Kafe', source: 'OSM' },
    { name: 'Baku Tea House', lat: 40.3730, lng: 49.8410, category: 'Çay Evi', source: 'OSM' },
    { name: 'Shusha Döner', lat: 39.7610, lng: 46.7490, category: 'Restoran', source: 'OSM' },
    { name: 'Dolma House Baku', lat: 40.3675, lng: 49.8330, category: 'Restoran', source: 'OSM' },
    { name: 'Sahil Cafe Lankaran', lat: 38.7550, lng: 48.8500, category: 'Kafe', source: 'OSM' }
];

// ============================================================
// 4. DOĞA ALANLARI (Nature Areas) - Yeşil
// ============================================================
const dogaPOI = [
    { name: 'Göygöl Milli Parkı', lat: 40.5833, lng: 46.3167, category: 'Milli Park', source: 'OSM' },
    { name: 'Şahdağ Milli Parkı', lat: 41.2833, lng: 48.0833, category: 'Milli Park', source: 'OSM' },
    { name: 'Hirkan Milli Parkı', lat: 38.6000, lng: 48.8000, category: 'Milli Park', source: 'OSM' },
    { name: 'Ağgöl Milli Parkı', lat: 40.0833, lng: 47.8333, category: 'Milli Park', source: 'OSM' },
    { name: 'Qızılağac Milli Parkı', lat: 39.1000, lng: 49.0000, category: 'Milli Park', source: 'OSM' },
    { name: 'Baku Sahil Parkı (Bulvar)', lat: 40.3710, lng: 49.8550, category: 'Şehir Parkı', source: 'OSM' },
    { name: 'Dağüstü Park (Baku)', lat: 40.3580, lng: 49.8220, category: 'Şehir Parkı', source: 'OSM' },
    { name: 'Tufandağ Kayak Merkezi', lat: 40.9820, lng: 47.8480, category: 'Kayak Merkezi', source: 'OSM' },
    { name: 'Şahdağ Kayak Merkezi', lat: 41.2870, lng: 48.0800, category: 'Kayak Merkezi', source: 'OSM' },
    { name: 'Nabran Sahili', lat: 41.5600, lng: 48.8800, category: 'Plaj', source: 'OSM' },
    { name: 'Bilgəh Sahili', lat: 40.5550, lng: 50.0800, category: 'Plaj', source: 'OSM' },
    { name: 'Afurja Şelalesi', lat: 41.1200, lng: 48.5800, category: 'Şelale', source: 'OSM' },
    { name: 'Mamirli Şelalesi', lat: 40.7000, lng: 48.4000, category: 'Şelale', source: 'OSM' },
    { name: 'Istisu Bulağı', lat: 40.6300, lng: 48.5000, category: 'Termal Kaynak', source: 'OSM' },
    { name: 'Naftalan Termal Merkezi', lat: 40.5067, lng: 46.8219, category: 'Termal Kaynak', source: 'OSM' },
    { name: 'Gobustan Açık Hava Müzesi', lat: 40.1060, lng: 49.3890, category: 'Tabiat Alanı', source: 'OSM' },
    { name: 'Çengen Dağı', lat: 40.3500, lng: 48.6500, category: 'Dağ', source: 'OSM' },
    { name: 'Yanardağ', lat: 40.5028, lng: 49.8911, category: 'Doğal Anıt', source: 'OSM' },
    { name: 'Bazar-Yurt Dağı', lat: 41.5167, lng: 46.6500, category: 'Dağ', source: 'OSM' },
    { name: 'Lankaran Sahili', lat: 38.7500, lng: 48.8600, category: 'Plaj', source: 'OSM' },
    { name: 'Babadağ', lat: 41.0167, lng: 48.3000, category: 'Dağ', source: 'OSM' },
    { name: 'Samur-Yalama Milli Parkı', lat: 41.8000, lng: 48.6000, category: 'Milli Park', source: 'OSM' },
    { name: 'Altıağac Milli Parkı', lat: 40.9000, lng: 48.8500, category: 'Milli Park', source: 'OSM' },
    { name: 'Ağsu Kanyonu', lat: 40.5500, lng: 48.3500, category: 'Kanyon', source: 'OSM' },
    { name: 'Naftalan Parkı', lat: 40.5070, lng: 46.8220, category: 'Termal Park', source: 'OSM' }
];

// ============================================================
// 5. KÜLTÜR MERKEZLERİ (Culture Centers) - Mor
// ============================================================
const kulturPOI = [
    { name: 'Haydar Aliyev Merkezi', lat: 40.3875, lng: 49.8609, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Azerbaycan Devlet Akademik Operası', lat: 40.3750, lng: 49.8410, category: 'Tiyatro', source: 'OSM' },
    { name: 'Azerbaycan Filarmonisi', lat: 40.3695, lng: 49.8380, category: 'Konser Salonu', source: 'OSM' },
    { name: 'Nizami Sinema Merkezi', lat: 40.3780, lng: 49.8520, category: 'Sinema', source: 'OSM' },
    { name: 'Gence Devlet Filarmonisi', lat: 40.6830, lng: 46.3610, category: 'Konser Salonu', source: 'OSM' },
    { name: 'Gence Devlet Dram Tiyatrosu', lat: 40.6820, lng: 46.3590, category: 'Tiyatro', source: 'OSM' },
    { name: 'Şeki Kültür Evi', lat: 41.1970, lng: 47.1590, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Lenkeran Kültür Merkezi', lat: 38.7540, lng: 48.8510, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Naxçıvan Kültür Sarayı', lat: 39.2110, lng: 45.4130, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Mingecevir Kültür Merkezi', lat: 40.7720, lng: 47.0510, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Sumgayıt Kültür Sarayı', lat: 40.5860, lng: 49.6340, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Museum of Modern Art Baku', lat: 40.3770, lng: 49.8560, category: 'Müze', source: 'OSM' },
    { name: 'YARAT Çağdaş Sanat Merkezi', lat: 40.3820, lng: 49.8700, category: 'Sanat Merkezi', source: 'OSM' },
    { name: 'Bakıxanov Kültür Evi', lat: 40.4000, lng: 49.9500, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Quba Kültür Merkezi', lat: 41.3630, lng: 48.5080, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Qebele Kültür Merkezi', lat: 40.9830, lng: 47.8460, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Şamaxı Kültür Evi', lat: 40.6280, lng: 48.6410, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Balakən Kültür Merkezi', lat: 41.7240, lng: 46.4060, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'İsmayıllı Kültür Evi', lat: 40.7880, lng: 48.1510, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Göygöl Kültür Merkezi', lat: 40.5810, lng: 46.3180, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Kürdəmir Kültür Sarayı', lat: 40.3400, lng: 48.1600, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Saatlı Kültür Evi', lat: 39.9400, lng: 48.3700, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Beyləqan Kültür Merkezi', lat: 39.7750, lng: 47.6170, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Ağcabədi Kültür Sarayı', lat: 40.0520, lng: 47.4590, category: 'Kültür Merkezi', source: 'OSM' },
    { name: 'Şuşa Kültür Merkezi', lat: 39.7620, lng: 46.7510, category: 'Kültür Merkezi', source: 'OSM' }
];

// ============================================================
// 6. ULAŞIM (Transportation) - Gri
// ============================================================
const ulasimPOI = [
    { name: 'Haydar Aliyev Uluslararası Havalimanı', lat: 40.4675, lng: 50.0467, category: 'Havalimanı', source: 'OSM' },
    { name: 'Gence Uluslararası Havalimanı', lat: 40.7333, lng: 46.3167, category: 'Havalimanı', source: 'OSM' },
    { name: 'Nahçıvan Havalimanı', lat: 39.1833, lng: 45.4500, category: 'Havalimanı', source: 'OSM' },
    { name: 'Lenkeran Havalimanı', lat: 38.7500, lng: 48.8167, category: 'Havalimanı', source: 'OSM' },
    { name: 'Yevlah Havalimanı', lat: 40.6333, lng: 47.1333, category: 'Havalimanı', source: 'OSM' },
    { name: 'Zaqatala Havalimanı', lat: 41.5667, lng: 46.6667, category: 'Havalimanı', source: 'OSM' },
    { name: 'Bakü Ana Tren Garı', lat: 40.3781, lng: 49.8494, category: 'Tren Garı', source: 'OSM' },
    { name: 'Gence Tren Garı', lat: 40.6780, lng: 46.3430, category: 'Tren Garı', source: 'OSM' },
    { name: 'Sumgayıt Tren Garı', lat: 40.5850, lng: 49.6560, category: 'Tren Garı', source: 'OSM' },
    { name: 'Bakü Uluslararası Otogarı', lat: 40.4111, lng: 49.8700, category: 'Otogar', source: 'OSM' },
    { name: 'Bakü Deniz Limanı', lat: 40.3680, lng: 49.8580, category: 'Liman', source: 'OSM' },
    { name: 'Bakü Metrosu - 28 May', lat: 40.3790, lng: 49.8460, category: 'Metro', source: 'OSM' },
    { name: 'Bakü Metrosu - İçerişehir', lat: 40.3660, lng: 49.8340, category: 'Metro', source: 'OSM' },
    { name: 'Gence Otogarı', lat: 40.6810, lng: 46.3550, category: 'Otogar', source: 'OSM' },
    { name: 'Nahçıvan Otogarı', lat: 39.2070, lng: 45.4090, category: 'Otogar', source: 'OSM' },
    { name: 'Mingecevir Limanı', lat: 40.7700, lng: 47.0480, category: 'Liman', source: 'OSM' },
    { name: 'Horadiz Tren İstasyonu', lat: 39.4500, lng: 47.3330, category: 'Tren Garı', source: 'OSM' },
    { name: 'Bakü Metrosu - Nizami', lat: 40.3770, lng: 49.8340, category: 'Metro', source: 'OSM' },
    { name: 'Bakü Metrosu - Gence Kapısı', lat: 40.3940, lng: 49.8700, category: 'Metro', source: 'OSM' },
    { name: 'Guba Otogarı', lat: 41.3590, lng: 48.5020, category: 'Otogar', source: 'OSM' }
];

// ============================================================
// 7. TURİZM BÖLGELERİ (Tourism Regions) - Kırmızı
// ============================================================
const turizmBolgePOI = [
    { name: 'Bakü Turizm Bölgesi', lat: 40.4093, lng: 49.8671, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Abşeron Turizm Bölgesi', lat: 40.4500, lng: 49.9000, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Gence-Kazak Turizm Bölgesi', lat: 40.6828, lng: 46.3606, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Şeki-Zaqatala Turizm Bölgesi', lat: 41.4167, lng: 46.6500, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Quba-Qusar Turizm Bölgesi', lat: 41.3600, lng: 48.5000, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Qebele-İsmayıllı Turizm Bölgesi', lat: 40.8500, lng: 47.9000, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Lenkeran-Astara Turizm Bölgesi', lat: 38.7000, lng: 48.8000, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Naxçıvan Turizm Bölgesi', lat: 39.2000, lng: 45.4000, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Şirvan-Salyan Turizm Bölgesi', lat: 39.6500, lng: 48.9000, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Dağlıq Qarabağ Turizm Bölgesi', lat: 39.7600, lng: 46.7500, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Naftalan Turizm ve Sağlık Bölgesi', lat: 40.5067, lng: 46.8219, category: 'Termal Bölge', source: 'OSM' },
    { name: 'Mingecevir Turizm Bölgesi', lat: 40.7700, lng: 47.0400, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Göygöl Turizm Bölgesi', lat: 40.5800, lng: 46.3100, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Şamaxı Turizm Bölgesi', lat: 40.6278, lng: 48.6428, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Qobustan Turizm Bölgesi', lat: 40.1000, lng: 49.4000, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Xızı Turizm Bölgesi', lat: 40.8000, lng: 49.0500, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Biləsuvar Turizm Bölgesi', lat: 39.4500, lng: 48.5500, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'İmişli Turizm Bölgesi', lat: 39.8700, lng: 48.0600, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Yardımlı Turizm Bölgesi', lat: 38.9200, lng: 48.2400, category: 'Turizm Bölgesi', source: 'OSM' },
    { name: 'Masallı Turizm Bölgesi', lat: 39.0200, lng: 48.6800, category: 'Turizm Bölgesi', source: 'OSM' }
];

// ============================================================
// TOPLU VERİ (Aggregated Data)
// ============================================================
// Tüm POI'leri kategorileriyle birlikte tek bir dizide toplar
const allPOIData = {
    konaklama: konaklamaPOI,
    tarihi: tarihiPOI,
    yemeicme: yemeicmePOI,
    doga: dogaPOI,
    kultur: kulturPOI,
    ulasim: ulasimPOI,
    turizm: turizmBolgePOI
};

// ============================================================
// KATEGORİ METADATA (Category Metadata)
// ============================================================
const categoryMeta = {
    konaklama: {
        label: '🏨 Konaklama',
        color: MARKER_COLORS.konaklama,
        count: konaklamaPOI.length,
        icon: '🏨'
    },
    tarihi: {
        label: '🏛️ Tarihi Yerler',
        color: MARKER_COLORS.tarihi,
        count: tarihiPOI.length,
        icon: '🏛️'
    },
    yemeicme: {
        label: '🍽️ Yeme-İçme',
        color: MARKER_COLORS.yemeicme,
        count: yemeicmePOI.length,
        icon: '🍽️'
    },
    doga: {
        label: '🌿 Doğa Alanları',
        color: MARKER_COLORS.doga,
        count: dogaPOI.length,
        icon: '🌿'
    },
    kultur: {
        label: '🎭 Kültür Merkezleri',
        color: MARKER_COLORS.kultur,
        count: kulturPOI.length,
        icon: '🎭'
    },
    ulasim: {
        label: '🚉 Ulaşım',
        color: MARKER_COLORS.ulasim,
        count: ulasimPOI.length,
        icon: '🚉'
    },
    turizm: {
        label: '📍 Turizm Bölgeleri',
        color: MARKER_COLORS.turizm,
        count: turizmBolgePOI.length,
        icon: '📍'
    }
};

// ============================================================
// GeoJSON dönüştürücü (istenirse GeoJSON formatında kullanılabilir)
// ============================================================
function convertToGeoJSON(poiArray) {
    return {
        type: 'FeatureCollection',
        features: poiArray.map(p => ({
            type: 'Feature',
            geometry: {
                type: 'Point',
                coordinates: [p.lng, p.lat]
            },
            properties: {
                name: p.name,
                category: p.category,
                source: p.source
            }
        }))
    };
}

// ============================================================
// Dışa aktarımlar (exports)
// ============================================================
// Bu değişkenler doğrudan harita.html içinde kullanılabilir.
// Ayrıca GeoJSON FeatureCollection olarak da her kategori için
// aşağıdaki gibi erişilebilir:
//   const otellerGeoJSON = convertToGeoJSON(konaklamaPOI);
