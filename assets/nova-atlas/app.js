/* Nova Atlas — static, read-only GitHub Pages map client. */

const DATA_ROOT = "data/nova-atlas";
let searchIndexPromise;

const COLORS = {
  NATURAL_RESOURCES: "#2e8d5a",
  HISTORICAL_CULTURAL: "#7b4aa0",
  ACCOMMODATION: "#e48629",
  FOOD_BEVERAGE: "#d85d4e",
  USER_CURATED: "#64747b",
  TRANSPORT: "#286ca1"
};

const GROUPS = [
  ["natural", "NATURAL_RESOURCES"],
  ["cultural", "HISTORICAL_CULTURAL"],
  ["accommodation", "ACCOMMODATION"],
  ["food", "FOOD_BEVERAGE"]
];

const layerFiles = {};
const loaded = new Set();
const loading = new Map();
const controls = {};
const wiredClickLayers = new Set();
let map;
let lastSearchResults = [];

const ICON_COLORS = {
  natural: "#2f8a55",
  cultural: "#78509b",
  accommodation: "#e4882e",
  food: "#d45b4b",
  transport: "#2b6ea4",
  rail: "#3e454a",
  bus: "#147b9e",
  user: "#64747b"
};

function iconImage(color, kind) {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, 64, 64);
  ctx.fillStyle = color;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 3.5;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";
  const path = new Path2D();
  const polygon = (points) => { ctx.beginPath(); points.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)); ctx.closePath(); ctx.fill(); ctx.stroke(); };
  if (kind.includes("peak")) polygon([[32, 7], [8, 53], [56, 53]]);
  else if (kind.includes("waterfall")) { polygon([[7, 12], [57, 12], [50, 26], [42, 21], [34, 30], [25, 22], [14, 31]]); ctx.beginPath(); ctx.moveTo(25, 31); ctx.lineTo(25, 54); ctx.moveTo(34, 30); ctx.lineTo(34, 57); ctx.moveTo(43, 27); ctx.lineTo(43, 51); ctx.stroke(); }
  else if (kind.includes("lake")) { ctx.beginPath(); ctx.ellipse(32, 34, 24, 15, 0, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.moveTo(10, 27); ctx.quadraticCurveTo(20, 19, 30, 27); ctx.quadraticCurveTo(40, 35, 54, 26); ctx.stroke(); }
  else if (kind.includes("protected")) { ctx.beginPath(); ctx.moveTo(32, 8); ctx.lineTo(12, 32); ctx.lineTo(23, 32); ctx.lineTo(13, 49); ctx.lineTo(51, 49); ctx.lineTo(41, 32); ctx.lineTo(52, 32); ctx.closePath(); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.moveTo(32, 49); ctx.lineTo(32, 59); ctx.stroke(); }
  else if (kind.includes("climatic")) { ctx.beginPath(); ctx.arc(32, 32, 12, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); for (let a = 0; a < 8; a++) { const x1 = 32 + Math.cos(a * Math.PI / 4) * 20; const y1 = 32 + Math.sin(a * Math.PI / 4) * 20; const x2 = 32 + Math.cos(a * Math.PI / 4) * 27; const y2 = 32 + Math.sin(a * Math.PI / 4) * 27; ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); } }
  else if (kind.includes("cave")) { ctx.beginPath(); ctx.arc(32, 44, 20, Math.PI, 0); ctx.lineTo(52, 54); ctx.lineTo(12, 54); ctx.closePath(); ctx.fill(); ctx.stroke(); }
  else if (kind.includes("viewpoint")) { polygon([[7, 51], [24, 28], [34, 39], [45, 21], [57, 51]]); ctx.beginPath(); ctx.arc(33, 19, 5, 0, Math.PI * 2); ctx.fillStyle = "#ffffff"; ctx.fill(); }
  else if (kind.startsWith("cultural_mosque")) { ctx.fillRect(17, 27, 30, 26); ctx.strokeRect(17, 27, 30, 26); ctx.beginPath(); ctx.arc(32, 27, 15, Math.PI, 0); ctx.fill(); ctx.stroke(); ctx.fillRect(10, 16, 7, 37); ctx.fillRect(47, 16, 7, 37); }
  else if (kind.includes("museum")) { ctx.fillRect(12, 20, 40, 7); ctx.strokeRect(12, 20, 40, 7); for (const x of [16, 26, 36, 46]) ctx.fillRect(x, 28, 5, 22); ctx.fillRect(9, 50, 46, 7); }
  else if (kind.includes("castle")) { polygon([[9, 18], [20, 18], [20, 11], [30, 11], [30, 18], [42, 18], [42, 9], [54, 9], [54, 54], [9, 54]]); ctx.beginPath(); ctx.moveTo(9, 31); ctx.lineTo(54, 31); ctx.stroke(); }
  else if (kind.includes("archaeology")) { ctx.fillRect(16, 18, 8, 35); ctx.fillRect(40, 18, 8, 35); ctx.fillRect(12, 14, 40, 6); ctx.fillRect(10, 52, 44, 6); }
  else if (kind.includes("heritage")) { polygon([[32, 6], [39, 24], [58, 25], [43, 36], [48, 55], [32, 44], [16, 55], [21, 36], [6, 25], [25, 24]]); }
  else if (kind.includes("monument")) { polygon([[32, 8], [47, 52], [17, 52]]); ctx.fillRect(11, 52, 42, 6); }
  else if (kind.includes("accommodation_camping")) { polygon([[7, 53], [32, 12], [57, 53]]); ctx.beginPath(); ctx.moveTo(32, 12); ctx.lineTo(32, 53); ctx.stroke(); }
  else if (kind.includes("accommodation_guesthouse")) { polygon([[8, 30], [32, 10], [56, 30], [52, 30], [52, 54], [12, 54], [12, 30]]); ctx.fillStyle = "#ffffff"; ctx.fillRect(27, 39, 10, 15); }
  else if (kind.includes("accommodation_resort")) { ctx.fillRect(27, 20, 6, 34); ctx.beginPath(); ctx.arc(30, 18, 15, Math.PI, Math.PI * 2); ctx.stroke(); ctx.beginPath(); ctx.arc(30, 18, 23, Math.PI, Math.PI * 2); ctx.stroke(); }
  else if (kind.includes("accommodation")) { ctx.fillRect(12, 30, 40, 22); ctx.strokeRect(12, 30, 40, 22); ctx.fillRect(18, 24, 8, 28); ctx.beginPath(); ctx.moveTo(26, 39); ctx.lineTo(48, 39); ctx.stroke(); }
  else if (kind.includes("food_cafe")) { ctx.fillRect(15, 22, 28, 25); ctx.strokeRect(15, 22, 28, 25); ctx.beginPath(); ctx.arc(44, 34, 8, -Math.PI / 2, Math.PI / 2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(12, 51); ctx.lineTo(51, 51); ctx.stroke(); }
  else if (kind.includes("food_local")) { ctx.beginPath(); ctx.arc(32, 35, 19, 0, Math.PI); ctx.fill(); ctx.stroke(); ctx.beginPath(); ctx.moveTo(14, 35); ctx.lineTo(50, 35); ctx.stroke(); }
  else if (kind.includes("food")) { ctx.beginPath(); ctx.moveTo(17, 12); ctx.lineTo(17, 54); ctx.moveTo(12, 12); ctx.lineTo(12, 29); ctx.quadraticCurveTo(17, 34, 22, 29); ctx.lineTo(22, 12); ctx.moveTo(44, 12); ctx.lineTo(44, 54); ctx.moveTo(39, 12); ctx.lineTo(50, 12); ctx.stroke(); }
  else if (kind.includes("transport_airport")) { polygon([[32, 6], [38, 27], [58, 38], [58, 44], [36, 38], [32, 58], [27, 38], [6, 44], [6, 38], [27, 27]]); }
  else if (kind.includes("transport_rail")) { ctx.fillRect(11, 15, 42, 34); ctx.strokeRect(11, 15, 42, 34); ctx.fillStyle = "#ffffff"; ctx.fillRect(18, 23, 10, 9); ctx.fillRect(36, 23, 10, 9); ctx.beginPath(); ctx.moveTo(18, 50); ctx.lineTo(12, 58); ctx.moveTo(46, 50); ctx.lineTo(52, 58); ctx.stroke(); }
  else if (kind.includes("transport_bus")) { ctx.fillRect(9, 19, 46, 31); ctx.strokeRect(9, 19, 46, 31); ctx.fillStyle = "#ffffff"; ctx.fillRect(16, 26, 13, 9); ctx.fillRect(35, 26, 13, 9); ctx.beginPath(); ctx.arc(20, 51, 4, 0, Math.PI * 2); ctx.arc(44, 51, 4, 0, Math.PI * 2); ctx.fill(); }
  else { ctx.beginPath(); ctx.arc(32, 32, 20, 0, Math.PI * 2); ctx.fill(); ctx.stroke(); }
  return ctx.getImageData(0, 0, 64, 64);
}

function registerIcons() {
  const ids = [
    "natural_peak", "natural_waterfall", "natural_lake", "natural_protected", "natural_climatic", "natural_cave", "natural_viewpoint",
    "cultural_mosque", "cultural_museum", "cultural_castle", "cultural_archaeology", "cultural_heritage", "cultural_monument", "cultural_historic",
    "accommodation_hotel", "accommodation_guesthouse", "accommodation_motel", "accommodation_camping", "accommodation_resort",
    "food_restaurant", "food_cafe", "food_local", "transport_airport", "transport_rail", "transport_bus", "user_curated", "generic_poi"
  ];
  ids.forEach((id) => {
    if (map.hasImage(id)) return;
    const prefix = id.split("_")[0];
    const color = id.startsWith("transport_airport") ? ICON_COLORS.transport : id.startsWith("transport_rail") ? ICON_COLORS.rail : id.startsWith("transport_bus") ? ICON_COLORS.bus : id.startsWith("user") ? ICON_COLORS.user : ICON_COLORS[prefix] || "#526974";
    map.addImage(id, iconImage(color, id), { pixelRatio: 2 });
  });
}

function setStatus(text) {
  const node = document.getElementById("data-status");
  if (node) node.textContent = text;
}

function fetchJson(path, options) {
  return fetch(path, options).then((response) => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  });
}

function loadSearchIndex() {
  if (!searchIndexPromise) searchIndexPromise = fetchJson(`${DATA_ROOT}/search.json`);
  return searchIndexPromise;
}

function normaliseText(value) {
  return String(value || "").toLocaleLowerCase("az-AZ").normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
}

function api(path, options) {
  if (options?.method && options.method !== "GET") return Promise.reject(new Error("Static read-only endpoint"));
  if (path === "/api/layers") return fetchJson(`${DATA_ROOT}/manifest.json`);
  if (path.startsWith("/api/layers/")) {
    const layerId = decodeURIComponent(path.slice("/api/layers/".length));
    const file = layerFiles[layerId]?.file || `${layerId}.geojson`;
    return fetchJson(`${DATA_ROOT}/${file}`);
  }
  if (path.startsWith("/api/search")) {
    const query = new URL(path, window.location.href).searchParams.get("query") || "";
    const needle = normaliseText(query);
    return loadSearchIndex().then((records) => ({
      results: records.filter((item) => normaliseText(`${item.label} ${item.rayon} ${item.group} ${item.subtype}`).includes(needle)).slice(0, 50)
    }));
  }
  if (path === "/api/rayons") {
    return fetchJson(`${DATA_ROOT}/rayons.geojson`).then((data) => ({
      rayons: (data.features || []).map((feature) => ({ name_az: rayonName(feature.properties || {}) })).filter((item) => item.name_az)
    }));
  }
  return Promise.reject(new Error(`Unknown static endpoint: ${path}`));
}

function sourceId(layerId) { return `src-${layerId}`; }

function makeSourceLayer(layerId, type, paint, layout = {}, extra = {}) {
  map.addLayer({ id: `layer-${layerId}`, type, source: sourceId(layerId), paint, layout, ...extra });
}

function loadGeoLayer(layerId) {
  if (loaded.has(layerId)) return Promise.resolve();
  if (loading.has(layerId)) return loading.get(layerId);
  if (!layerFiles[layerId]) return Promise.reject(new Error(`Unknown layer ${layerId}`));
  const request = api(`/api/layers/${layerId}`).then((data) => {
    map.addSource(sourceId(layerId), { type: "geojson", data });
    loaded.add(layerId);
    addGeoStyle(layerId);
  }).finally(() => loading.delete(layerId));
  loading.set(layerId, request);
  return request;
}

function addGeoStyle(layerId) {
  if (layerId === "country") {
    makeSourceLayer("country", "fill", { "fill-color": "#eef0e3", "fill-opacity": 0.28 });
    map.addLayer({ id: "country-outline", type: "line", source: sourceId("country"), paint: { "line-color": "#233f51", "line-width": 2.0 } });
  } else if (layerId === "rayons") {
    map.addLayer({ id: "rayon-lines", type: "line", source: sourceId("rayons"), paint: { "line-color": "#7d8a8c", "line-width": 0.55, "line-opacity": 0.70, "line-dasharray": [2, 2] } });
  } else if (layerId === "rivers_major") {
    map.addLayer({ id: "rivers-major-lines", type: "line", source: sourceId(layerId), minzoom: 5, paint: { "line-color": "#3c99be", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1.0, 9, 2.1], "line-opacity": 0.85 } });
  } else if (layerId === "lakes_reservoirs") {
    map.addLayer({ id: "lakes-fill", type: "fill", source: sourceId(layerId), minzoom: 5, paint: { "fill-color": "#75b9d0", "fill-opacity": 0.48 } });
    map.addLayer({ id: "lakes-outline", type: "line", source: sourceId(layerId), minzoom: 5, paint: { "line-color": "#4d9fbe", "line-width": 0.6 } });
  } else if (layerId === "protected_areas") {
    map.addLayer({ id: "protected-fill", type: "fill", source: sourceId(layerId), minzoom: 5, paint: { "fill-color": "#75a96f", "fill-opacity": 0.20 } });
    map.addLayer({ id: "protected-outline", type: "line", source: sourceId(layerId), paint: { "line-color": "#568b5e", "line-width": 0.8, "line-opacity": 0.65 } });
  } else if (layerId === "roads_primary") {
    map.addLayer({ id: "roads-primary-lines", type: "line", source: sourceId(layerId), minzoom: 5, paint: { "line-color": "#a9563f", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1.35, 9, 3.0], "line-opacity": 0.92 } });
  } else if (layerId === "roads_secondary") {
    map.addLayer({ id: "roads-secondary-lines", type: "line", source: sourceId(layerId), minzoom: 7, paint: { "line-color": "#d18a56", "line-width": ["interpolate", ["linear"], ["zoom"], 7, 0.9, 10, 1.8], "line-opacity": 0.82 } });
  } else if (layerId === "roads_local") {
    map.addLayer({ id: "roads-local-lines", type: "line", source: sourceId(layerId), minzoom: 8, paint: { "line-color": "#9f8f83", "line-width": ["interpolate", ["linear"], ["zoom"], 8, 0.45, 11, 1.05, 14, 1.65], "line-opacity": 0.62 } });
  } else if (layerId === "railways") {
    map.addLayer({ id: "railway-lines", type: "line", source: sourceId(layerId), minzoom: 5, paint: { "line-color": "#3e454a", "line-width": 1.3, "line-dasharray": [2, 2], "line-opacity": 0.90 } });
  } else if (layerId === "rail_stations") {
    addTransportPoint("rail_stations", "#3e454a", "square");
  } else if (layerId === "airports") {
    addTransportPoint("airports", COLORS.TRANSPORT, "circle");
  } else if (layerId === "bus_terminals") {
    addTransportPoint("bus_terminals", "#147b9e", "diamond");
  } else if (layerId === "settlements_major") {
    map.addLayer({ id: "settlement-dots", type: "circle", source: sourceId(layerId), minzoom: 5.5, paint: { "circle-radius": 2.3, "circle-color": "#485e67", "circle-stroke-color": "#fbfaf5", "circle-stroke-width": 1 } });
    map.addLayer({ id: "settlement-labels", type: "symbol", source: sourceId(layerId), minzoom: 6, layout: { "text-field": ["get", "label"], "text-size": 11, "text-font": ["Open Sans Regular"], "text-offset": [0.6, 0], "text-allow-overlap": false, "text-ignore-placement": false }, paint: { "text-color": "#36525f", "text-halo-color": "#f7f5ee", "text-halo-width": 1.5 } });
  } else if (["atlas_core", "atlas_core_country", "natural", "cultural", "accommodation", "food", "user_curated"].includes(layerId)) {
    addTourismLayers(layerId);
  }
  wireMapClicks();
}

function addTransportPoint(layerId, color, shape) {
  const iconId = layerId === "airports" ? "transport_airport" : layerId === "rail_stations" ? "transport_rail" : "transport_bus";
  map.addLayer({ id: `${layerId}-points`, type: "symbol", source: sourceId(layerId), minzoom: 5, layout: { "icon-image": iconId, "icon-size": ["interpolate", ["linear"], ["zoom"], 5, 0.48, 10, 0.72], "icon-allow-overlap": false, "icon-ignore-placement": false, "symbol-sort-key": 1 } });
  map.addLayer({ id: `${layerId}-labels`, type: "symbol", source: sourceId(layerId), minzoom: 8, layout: { "text-field": ["coalesce", ["get", "name_az"], ["get", "name"], ["get", "name_en"], ""], "text-size": 10, "text-font": ["Open Sans Regular"], "text-offset": [0.7, 0], "text-optional": true, "text-allow-overlap": false }, paint: { "text-color": "#334c59", "text-halo-color": "#f7f5ee", "text-halo-width": 1.4 } });
}

function addTourismLayers(layerId) {
  if (layerId === "atlas_core" || layerId === "atlas_core_country") {
    const prefix = layerId === "atlas_core_country" ? "corec" : "core";
    const minzoom = layerId === "atlas_core_country" ? 0 : 8;
    const maxzoom = layerId === "atlas_core_country" ? 8 : 24;
    GROUPS.forEach(([short, group]) => {
      map.addLayer({ id: `${prefix}-${short}`, type: "symbol", source: sourceId(layerId), minzoom, maxzoom, layout: { "icon-image": ["coalesce", ["get", "icon_id"], "generic_poi"], "icon-size": ["interpolate", ["linear"], ["zoom"], 5, 0.68, 10, 0.95, 13, 1.08], "icon-allow-overlap": false, "icon-ignore-placement": false, "symbol-sort-key": ["coalesce", ["get", "display_rank"], 999999] }, filter: ["==", ["get", "thesis_group"], group] });
      map.addLayer({ id: `${prefix}-${short}-labels`, type: "symbol", source: sourceId(layerId), minzoom: Math.max(8, minzoom), maxzoom, layout: { "text-field": ["coalesce", ["get", "label"], ""], "text-size": 10, "text-font": ["Open Sans Regular"], "text-offset": [0.9, 0], "text-optional": true, "text-allow-overlap": false, "text-ignore-placement": false }, paint: { "text-color": COLORS[group], "text-halo-color": "#fbfaf5", "text-halo-width": 1.5 }, filter: ["==", ["get", "thesis_group"], group] });
    });
    return;
  }
  const group = GROUPS.find(([short]) => short === layerId)?.[1] || "USER_CURATED";
  map.addLayer({ id: `all-${layerId}`, type: "symbol", source: sourceId(layerId), minzoom: layerId === "user_curated" ? 10 : 8, layout: { "icon-image": ["coalesce", ["get", "icon_id"], "generic_poi"], "icon-size": layerId === "user_curated" ? 0.42 : ["interpolate", ["linear"], ["zoom"], 8, 0.50, 10, 0.66, 13, 0.82], "icon-allow-overlap": false, "icon-ignore-placement": false, "symbol-sort-key": ["coalesce", ["get", "display_rank"], 999999] } });
}

function setVisibility(prefixes, visible) {
  prefixes.forEach((id) => {
    if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
  });
}

function controlLayerIds(control) {
  return {
    physical: ["physical-relief"],
    rayons: ["rayon-lines"],
    hydro: ["rivers-major-lines", "lakes-fill", "lakes-outline"],
    protected: ["protected-fill", "protected-outline"],
    natural: ["corec-natural", "corec-natural-labels", "core-natural", "core-natural-labels", "all-natural"],
    cultural: ["corec-cultural", "corec-cultural-labels", "core-cultural", "core-cultural-labels", "all-cultural"],
    accommodation: ["corec-accommodation", "corec-accommodation-labels", "core-accommodation", "core-accommodation-labels", "all-accommodation"],
    food: ["corec-food", "corec-food-labels", "core-food", "core-food-labels", "all-food"],
    user_curated: ["all-user_curated"],
    transport: ["airports-points", "airports-labels"],
    rail: ["railway-lines", "rail_stations-points", "rail_stations-labels"],
    bus: ["bus_terminals-points", "bus_terminals-labels"],
    roads: ["roads-primary-lines", "roads-secondary-lines"],
    local_roads: ["roads-local-lines"]
  }[control] || [];
}

function updateControl(control) {
  const checked = controls[control]?.checked ?? false;
  const needed = control === "physical" ? Promise.resolve() : ensureControlLoaded(control);
  needed.then(() => setVisibility(controlLayerIds(control), checked)).catch((error) => {
    console.error(error);
    setStatus("Bir katman yüklenemedi");
  });
}

function ensureControlLoaded(control) {
  const mapping = {
    physical: [], rayons: ["rayons"], hydro: ["rivers_major", "lakes_reservoirs"], protected: ["protected_areas"],
    natural: ["atlas_core", "natural"], cultural: ["atlas_core", "cultural"], accommodation: ["atlas_core", "accommodation"], food: ["atlas_core", "food"], user_curated: ["user_curated"],
    transport: ["airports"], rail: ["railways", "rail_stations"], bus: ["bus_terminals"], roads: ["roads_primary", "roads_secondary"], local_roads: ["roads_local"]
  };
  return Promise.all((mapping[control] || []).map(loadGeoLayer)).then(() => undefined);
}

function updateZoomUI() {
  const zoom = map.getZoom();
  const note = document.getElementById("zoom-note");
  if (zoom < 8) note.textContent = "Ülke görünümü · Atlas Core";
  else if (zoom < 10) note.textContent = "Bölgesel görünüm · master POI katmanları";
  else note.textContent = "Yakın görünüm · hizmetler ve kullanıcı KML";
  document.getElementById("scale-help").textContent = zoom < 8 ? "Ülke görünümünde yalnız Atlas Core ve ana ağlar görünür." : zoom < 10 ? "Yakınlaştıkça doğal, kültürel, konaklama ve yeme-içme envanteri açılır." : "Rayon ölçeğinde kullanıcı KML’si ve ayrıntılı hizmet noktaları açılır.";
  const lazy = ["natural", "cultural", "accommodation", "food"];
  if (zoom >= 8) Promise.all(lazy.filter((key) => controls[key]?.checked).map((key) => ensureControlLoaded(key).then(() => updateControl(key)))).catch(console.error);
  if (zoom >= 10 && controls.user_curated?.checked) ensureControlLoaded("user_curated").then(() => updateControl("user_curated")).catch(console.error);
}

function showFeature(properties) {
  const card = document.getElementById("feature-card");
  const name = properties.label || properties.name_az || properties.name || properties.name_en || "Adsız kayıt";
  const group = properties.thesis_group || properties.group || "";
  const subtype = properties.thesis_subtype || properties.subtype || "";
  const status = properties.verification_status || properties.status || "";
  const rayon = properties.rayon || properties.rayon_name_az || properties.official_city || "";
  const source = properties.source_role || properties.source_primary || "";
  const details = [];
  const numberValue = (value, suffix = "") => {
    if (value === undefined || value === null || value === "" || Number.isNaN(Number(value))) return "";
    return `${Number(value).toLocaleString("tr-TR", { maximumFractionDigits: 1 })}${suffix}`;
  };
  const elevation = numberValue(properties.elevation_m, " m");
  const slope = numberValue(properties.slope_deg, "°");
  const road = numberValue(properties.osm_route_distance_km, " km");
  const rail = numberValue(properties.nearest_rail_station_km, " km");
  const airport = numberValue(properties.nearest_airport_km, " km");
  if (elevation) details.push(`Yükseklik: ${escapeHtml(elevation)}`);
  if (slope) details.push(`Eğim: ${escapeHtml(slope)}`);
  if (properties.terrain_context) details.push(`Fiziki bağlam: ${escapeHtml(properties.terrain_context)}`);
  if (properties.landcover_class) details.push(`Arazi örtüsü: ${escapeHtml(properties.landcover_class)}`);
  if (road) details.push(`OSM yol məsafəsi: ${escapeHtml(road)}`);
  if (rail) details.push(`En yakın demiryolu: ${escapeHtml(rail)}`);
  if (airport) details.push(`En yakın havaalanı: ${escapeHtml(airport)}`);
  if (properties.access_mode_status) details.push(`Erişim: ${escapeHtml(properties.access_mode_status)}`);
  const nearbySummary = (value, label) => {
    if (!value) return;
    try {
      const parsed = typeof value === "string" ? JSON.parse(value) : value;
      const count = Number(parsed.count || 0);
      const categories = parsed.category_summary ? Object.entries(parsed.category_summary).map(([key, item]) => `${key}: ${item}`).join(", ") : "";
      if (count || categories) details.push(`${label}: ${count}${categories ? ` (${escapeHtml(categories)})` : ""}`);
    } catch (_) { /* malformed optional enrichment is not a blocking map error */ }
  };
  nearbySummary(properties.nearby_accommodation, "Yakındaki konaklama");
  nearbySummary(properties.nearby_food, "Yakındaki yeme-içme");
  nearbySummary(properties.nearby_transport, "Yakındaki ulaşım");
  const primary = properties.source_primary ? `<br>Əsas mənbə: ${escapeHtml(properties.source_primary)}` : "";
  const validUrl = (value) => {
    const text = String(value || "").trim();
    if (!/^https?:\/\//i.test(text)) return "";
    try {
      const url = new URL(text);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "";
    } catch (_) { return ""; }
  };
  const links = [];
  [["Resmî kanıt", properties.official_evidence_source], ["Kaynak sayfası", properties.semantic_source_url], ["Miras kaynağı", properties.heritage_source_url], ["Google Maps", properties.google_maps_url]].forEach(([label, value]) => {
    const url = validUrl(value);
    if (url && !links.some((item) => item[1] === url)) links.push([label, url]);
  });
  const imageUrl = validUrl(properties.image_url || properties.photo_url || properties.thumbnail_url);
  const imageHtml = imageUrl ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(name)} görseli" loading="lazy" referrerpolicy="no-referrer">` : "";
  const linksHtml = links.length ? `<div class="source-links">${links.map(([label, url]) => `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`).join("")}</div>` : "";
  card.innerHTML = `<button aria-label="Kapat">×</button><h3>${escapeHtml(name)}</h3><p><b>${escapeHtml(group)}</b>${subtype ? ` · ${escapeHtml(subtype)}` : ""}<br>${rayon ? `Rayon: ${escapeHtml(rayon)}<br>` : ""}${status ? `Durum: ${escapeHtml(status)}<br>` : ""}${source ? `Kaynak rolü: ${escapeHtml(source)}` : ""}${primary}${details.length ? `<br>${details.join("<br>")}` : ""}</p>${imageHtml}${linksHtml}`;
  card.classList.remove("hidden");
  card.querySelector("button").onclick = () => card.classList.add("hidden");
}

function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char])); }

function wireMapClicks() {
  ["corec-natural", "corec-cultural", "corec-accommodation", "corec-food", "core-natural", "core-cultural", "core-accommodation", "core-food", "all-natural", "all-cultural", "all-accommodation", "all-food", "all-user_curated", "airports-points", "rail_stations-points", "bus_terminals-points", "settlement-dots"].forEach((layerId) => {
    if (!map.getLayer(layerId) || wiredClickLayers.has(layerId)) return;
    map.on("click", layerId, (event) => {
      const feature = event.features?.[0];
      if (feature) showFeature(feature.properties || {});
    });
    map.on("mouseenter", layerId, () => map.getCanvas().style.cursor = "pointer");
    map.on("mouseleave", layerId, () => map.getCanvas().style.cursor = "");
    wiredClickLayers.add(layerId);
  });
}

function flyToResult(item) {
  map.flyTo({ center: [item.lon, item.lat], zoom: Math.max(10, map.getZoom()), essential: true });
  setTimeout(() => showFeature({ label: item.label, thesis_group: item.group, thesis_subtype: item.subtype, rayon: item.rayon, verification_status: item.status, source_role: item.source_role }), 350);
  document.getElementById("search-results").classList.add("hidden");
}

function renderSearch(results) {
  const node = document.getElementById("search-results");
  node.innerHTML = "";
  results.slice(0, 10).forEach((item) => {
    const button = document.createElement("button");
    button.innerHTML = `<b>${escapeHtml(item.label)}</b><small>${escapeHtml(item.rayon || "Rayon qeyd olunmayıb")} · ${escapeHtml(item.group || item.source_role || "")}</small>`;
    button.onclick = () => flyToResult(item);
    node.appendChild(button);
  });
  node.classList.toggle("hidden", results.length === 0);
}

function initSearch() {
  const input = document.getElementById("search");
  let timer;
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      const value = input.value.trim();
      if (!value) { document.getElementById("search-results").classList.add("hidden"); return; }
      api(`/api/search?query=${encodeURIComponent(value)}`).then((data) => { lastSearchResults = data.results || []; renderSearch(lastSearchResults); }).catch(() => setStatus("Arama başarısız"));
    }, 180);
  });
}

function initNova() {
  const send = () => {
    const input = document.getElementById("nova-input");
    const answer = document.getElementById("nova-answer");
    if (!input.value.trim()) return;
    const question = input.value.trim();
    const needle = normaliseText(question);
    answer.textContent = "Nova Atlas yayınlanmış kataloğu kontrol ediyor…";
    loadSearchIndex().then((records) => {
      const rayonNames = [...new Set(records.map((item) => item.rayon).filter(Boolean))];
      const rayon = rayonNames.find((name) => {
        const key = normaliseText(name).replace(/\s+(rayonu|rayon|şəhəri|şəhər)$/u, "").trim();
        return key.length > 2 && needle.includes(key);
      });
      const groupTerms = [
        [["doğal", "tebii", "natural"], "NATURAL_RESOURCES", "doğal kaynak"],
        [["kültür", "meden", "tarixi", "tarih"], "HISTORICAL_CULTURAL", "tarihî/kültürel"],
        [["otel", "hotel", "konaklama", "yerleş"], "ACCOMMODATION", "konaklama"],
        [["restoran", "kafe", "yeme", "içme", "qida"], "FOOD_BEVERAGE", "yeme-içme"],
        [["ulaşım", "neqliyyat", "airport", "havaliman", "demiryolu", "avtovağzal"], "TRANSPORT", "ulaşım"]
      ];
      const group = groupTerms.find(([terms]) => terms.some((term) => needle.includes(normaliseText(term))));
      let matches = records;
      if (rayon) matches = matches.filter((item) => normaliseText(item.rayon) === normaliseText(rayon));
      if (group) matches = matches.filter((item) => item.group === group[1]);
      if (!rayon && !group) matches = records.filter((item) => normaliseText(`${item.label} ${item.rayon} ${item.group} ${item.subtype}`).includes(needle));
      if (!matches.length) {
        answer.textContent = "Yayınlanmış katalogda bu sorguyla eşleşen kayıt bulunamadı. Bu sonuç veri yokluğu değil, yalnız mevcut web paketinin kapsamıdır.";
        return;
      }
      const examples = matches.slice(0, 5).map((item) => item.label).join(", ");
      const scope = [rayon, group?.[2]].filter(Boolean).join(" · ") || "arama";
      answer.textContent = `${scope}: ${matches.length.toLocaleString("tr-TR")} eşleşme. Örnekler: ${examples}${matches.length > 5 ? "…" : ""}`;
    }).catch(() => { answer.textContent = "Nova Atlas statik kataloğu okunamadı."; });
  };
  document.getElementById("nova-send").onclick = send;
  document.getElementById("nova-input").addEventListener("keydown", (event) => { if (event.key === "Enter") send(); });
}

function initStats(stats) {
  const items = [[stats.atlas_core_country || 0, "Ülke seçkisi"], [stats.atlas_core, "Atlas Core toplam"], [stats.natural, "Doğal kayıt"], [stats.cultural, "Kültürel kayıt"], [stats.transport?.airports || 0, "Havalimanı"]];
  const node = document.getElementById("stats");
  node.innerHTML = items.map(([value, label]) => `<div class="stat"><strong>${Number(value || 0).toLocaleString("tr-TR")}</strong><span>${label}</span></div>`).join("");
}

function initCountryIndex() {
  api("/api/layers/atlas_core_country").then((data) => {
    const node = document.getElementById("country-index");
    if (!node) return;
    const features = (data.features || []).sort((a, b) => Number(a.properties?.display_rank || 999999) - Number(b.properties?.display_rank || 999999));
    node.innerHTML = features.map((feature, index) => {
      const p = feature.properties || {};
      const label = p.label || p.name_az || "İsimsiz kayıt";
      const elevation = p.elevation_m !== undefined && p.elevation_m !== null && p.elevation_m !== "" ? ` · ${Number(p.elevation_m).toLocaleString("tr-TR", { maximumFractionDigits: 0 })} m` : "";
      return `<button class="index-item" type="button" data-index="${index}"><span class="index-no">${String(index + 1).padStart(2, "0")}</span><span><b>${escapeHtml(label)}</b><small>${escapeHtml(p.rayon || "Rayon qeyd olunmayıb")}${elevation}</small></span></button>`;
    }).join("");
    node.querySelectorAll(".index-item").forEach((button, index) => button.onclick = () => {
      const feature = features[index];
      const p = feature.properties || {};
      const coordinates = feature.geometry?.coordinates;
      if (coordinates) map.flyTo({ center: coordinates, zoom: Math.max(8, map.getZoom()), essential: true });
      showFeature(p);
    });
  }).catch(() => {});
}

function rayonName(properties) {
  return properties.name_az || properties.rayon_name_az || properties.adm1_name1 || properties.adm1_name || properties.NAME_1 || properties.name || "";
}

function featureBounds(feature) {
  const bounds = [[Infinity, Infinity], [-Infinity, -Infinity]];
  const visit = (coordinates) => {
    if (!Array.isArray(coordinates)) return;
    if (coordinates.length >= 2 && Number.isFinite(coordinates[0]) && Number.isFinite(coordinates[1])) {
      bounds[0][0] = Math.min(bounds[0][0], coordinates[0]);
      bounds[0][1] = Math.min(bounds[0][1], coordinates[1]);
      bounds[1][0] = Math.max(bounds[1][0], coordinates[0]);
      bounds[1][1] = Math.max(bounds[1][1], coordinates[1]);
      return;
    }
    coordinates.forEach(visit);
  };
  visit(feature.geometry?.coordinates);
  return Number.isFinite(bounds[0][0]) ? bounds : null;
}

function initRayonExport() {
  const input = document.getElementById("rayon-name");
  const button = document.getElementById("rayon-generate");
  const result = document.getElementById("rayon-result");
  const card = document.getElementById("rayon-preview-card");
  if (card) card.remove();
  if (!input || !button) return;
  let rayons = [];
  const canonical = (value) => normaliseText(value).replace(/\s+(rayonu|rayon|şəhəri|şəhər)$/u, "").trim();
  fetchJson(`${DATA_ROOT}/rayons.geojson`).then((data) => {
    rayons = (data.features || []).map((feature) => ({ feature, name: rayonName(feature.properties || {}) })).filter((item) => item.name);
    const list = document.getElementById("rayon-options");
    rayons.map((item) => item.name).sort((a, b) => a.localeCompare(b, "az")).forEach((name) => {
      const option = document.createElement("option");
      option.value = name;
      list.appendChild(option);
    });
  }).catch(() => { result.textContent = "Rayon kataloğu yüklenemedi."; });
  const run = () => {
    const typed = input.value.trim();
    if (!typed) { result.textContent = "Rayon adını yazın."; return; }
    const match = rayons.find((item) => canonical(item.name) === canonical(typed));
    if (!match) { result.textContent = "Bu adla rayon tapılmadı. Məsələn: Quba, Qusar, Şəki."; return; }
    const bounds = featureBounds(match.feature);
    input.value = match.name;
    if (bounds) map.fitBounds(bounds, { padding: 70, duration: 900, maxZoom: 10.5 });
    result.textContent = `${match.name} görünümünə keçildi. Ayrıntı üçün turizm katmanlarını ve isterseniz “Yan yollar”ı açın.`;
  };
  button.onclick = run;
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") run(); });
}

function init() {
  api("/api/layers").then((catalog) => {
    Object.assign(layerFiles, catalog.layers);
    initStats(catalog.stats);
    const relief = catalog.layers.physical_relief;
    const style = { version: 8, glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf", sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19, attribution: "© OpenStreetMap contributors" } }, layers: [{ id: "osm-base", type: "raster", source: "osm", paint: { "raster-opacity": 0.30, "raster-saturation": -0.25, "raster-contrast": -0.04 } }] };
    map = new maplibregl.Map({ container: "map", style, center: [47.6, 40.35], zoom: 5.8, maxZoom: 16, attributionControl: true, cooperativeGestures: true });
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-left");
    map.addControl(new maplibregl.ScaleControl({ maxWidth: 140, unit: "metric" }), "bottom-left");
    map.on("load", () => {
      registerIcons();
      if (relief && relief.west !== undefined) {
        map.addSource("src-physical", { type: "image", url: `${DATA_ROOT}/${relief.file}`, coordinates: [[relief.west, relief.north], [relief.east, relief.north], [relief.east, relief.south], [relief.west, relief.south]] });
        map.addLayer({ id: "physical-relief", type: "raster", source: "src-physical", paint: { "raster-opacity": 0.72, "raster-saturation": -0.12, "raster-contrast": 0.02 } });
      }
      Promise.all(["country", "rayons", "atlas_core_country", "roads_primary", "roads_secondary", "rivers_major", "lakes_reservoirs", "protected_areas", "settlements_major", "airports", "railways", "rail_stations", "bus_terminals"].map(loadGeoLayer)).then(() => {
        setVisibility(["rayon-lines", "rivers-major-lines", "lakes-fill", "lakes-outline", "protected-fill", "protected-outline", "roads-primary-lines", "roads-secondary-lines", "railway-lines", "airports-points", "rail_stations-points", "bus_terminals-points", "settlement-dots", "settlement-labels", "corec-natural", "corec-cultural", "corec-accommodation", "corec-food"], true);
        setStatus("Yerel GIS kataloğu hazır");
        map.fitBounds([[44.65, 38.25], [50.95, 42.00]], { padding: 18, duration: 0 });
      }).catch((error) => { console.error(error); setStatus("Bazı temel katmanlar yüklenemedi"); });
      wireMapClicks();
    });
    map.on("zoomend", updateZoomUI);
    document.querySelectorAll("input[data-layer]").forEach((input) => { controls[input.dataset.layer] = input; input.addEventListener("change", () => { if (input.dataset.layer === "physical") setVisibility(["physical-relief"], input.checked); else updateControl(input.dataset.layer); }); });
    document.getElementById("reset-view").onclick = () => {
      map.fitBounds([[44.65, 38.25], [50.95, 42.00]], { padding: 18, duration: 800 });
      document.getElementById("feature-card")?.classList.add("hidden");
    };
    const panelToggle = document.getElementById("panel-toggle");
    const controlPanel = document.querySelector(".control-panel");
    panelToggle.onclick = () => {
      const collapsed = controlPanel.classList.toggle("collapsed");
      panelToggle.setAttribute("aria-label", collapsed ? "Paneli aç" : "Paneli daralt");
    };
    initSearch();
    initNova();
    initCountryIndex();
    initRayonExport();
  }).catch((error) => { console.error(error); setStatus("Nova Atlas başlatılamadı"); });
}

init();
