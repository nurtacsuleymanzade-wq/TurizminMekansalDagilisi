#!/usr/bin/env python3
"""
Accommodation Spatial Analysis & Map Generation
Research-grade: Moran's I, LISA, Hot Spot, KDE, choropleths, bivariate, animation
"""
import os, sys, json, warnings, math
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import matplotlib.ticker as ticker
from shapely.geometry import Point
from scipy import sparse
warnings.filterwarnings('ignore')

# ── Spatial libraries ──
try:
    import libpysal
    from esda.moran import Moran, Moran_Local
    from splot.esda import plot_moran, plot_local_autocorrelation, lisa_cluster
except:
    print("WARNING: Cannot import esda/splot. Some spatial analyses will be skipped.")
    libpysal = None

try:
    import contextily as ctx
except:
    ctx = None
    print("WARNING: contextily not installed. Maps will not have basemaps.")

# ── Paths ──
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed", "accommodation")
MAPS = os.path.join(BASE, "models", "maps", "accommodation")
GEO = os.path.join(BASE, "data", "geojson")
FRAMES = os.path.join(MAPS, "animation_frames")
os.makedirs(MAPS, exist_ok=True)
os.makedirs(FRAMES, exist_ok=True)

# ── Style ──
BG = '#0f0f1a'
TEXT = '#e0e0e0'
ACCENT = '#3498db'
RED = '#e74c3c'
GREEN = '#2ecc71'
ORANGE = '#f39c12'
DARK_CARD = '#1a1f2e'
BORDER = '#2a2a3a'

plt.rcParams.update({
    'figure.facecolor': BG, 'axes.facecolor': BG,
    'axes.edgecolor': BORDER, 'axes.labelcolor': TEXT,
    'text.color': TEXT, 'axes.titlecolor': TEXT,
    'xtick.color': TEXT, 'ytick.color': TEXT,
    'grid.color': BORDER, 'grid.alpha': 0.3,
    'font.family': 'sans-serif',
})

# ── Load data ──
def load_data():
    print("Loading data...")
    panel = pd.read_csv(os.path.join(PROC, 'regional_panel.csv'))
    gdf = gpd.read_file(os.path.join(GEO, 'azerbaijan_rayon_boundaries.geojson'))
    
    # Get latest year with most complete data
    valid_counts = panel.groupby('year').apply(lambda x: x['guests'].notna().sum())
    best_year = valid_counts.idxmax()
    print(f"  Best year for analysis: {best_year} ({valid_counts[best_year]} regions with data)")
    
    # Also try latest year
    latest_year = panel['year'].max()
    print(f"  Latest year: {latest_year}")
    
    # Merge panel with geometry
    def norm(s):
        s = str(s).lower().replace('şəhəri','').replace('rayonu','').replace('şəhər','').replace('\\n',' ').replace('\n',' ').strip()
        return s
    
    adm1_norm = {norm(k): k for k in gdf['adm1_name']}
    
    panel_merged = panel.merge(gdf[['adm1_name', 'geometry']], left_on='rayon', right_on='adm1_name', how='left')
    # Try norm match for unmatched
    unmatched = panel_merged[panel_merged['geometry'].isna()]['rayon'].unique()
    if len(unmatched) > 0:
        for r in unmatched:
            n = norm(r)
            for an, adm1 in adm1_norm.items():
                if n in an or an in n:
                    mask = panel_merged['rayon'] == r
                    panel_merged.loc[mask, 'adm1_name'] = adm1
                    panel_merged.loc[mask, 'geometry'] = gdf[gdf['adm1_name']==adm1]['geometry'].values[0]
                    break
    
    gdf_panel = gpd.GeoDataFrame(panel_merged[panel_merged['geometry'].notna()], geometry='geometry', crs='EPSG:4326')
    gdf_panel = gdf_panel.to_crs('EPSG:3857')
    
    print(f"  Panel with geometry: {len(gdf_panel)} rows")
    return panel, gdf_panel, best_year, latest_year


# ── Spatial Analysis ──
def run_spatial_analysis(gdf_panel, year):
    """Run Moran's I, LISA, Getis-Ord Gi*, KDE for key indicators."""
    print(f"\n=== Spatial Analysis for {year} ===")
    
    # Indicators to analyze
    base_indicators = ['capacity', 'nights', 'guests', 'revenue', 'employees']
    derived_indicators = ['hotel_density', 'revenue_per_capacity', 'foreign_tourist_ratio']
    indicators = base_indicators + derived_indicators
    
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    if len(year_data) == 0:
        print(f"  No data for year {year}")
        return {}
    
    results = {'year': int(year), 'indicators': {}}
    
    # Build W matrix
    w = None
    if libpysal:
        try:
            from libpysal.weights import Queen
            # Ensure geometry is valid
            w = Queen.from_dataframe(year_data, silence_warnings=True)
            w.transform = 'r'
            print(f"  Queen weights: {w.n} regions, {w.s0:.2f} total weight")
        except Exception as e:
            print(f"  WARNING: Could not build spatial weights: {e}")
    else:
        # Simple distance-based weights
        try:
            centroids = year_data.geometry.centroid
            coords = np.array([(c.x, c.y) for c in centroids])
            from sklearn.neighbors import NearestNeighbors
            nn = NearestNeighbors(n_neighbors=5)
            nn.fit(coords)
            distances, indices = nn.kneighbors(coords)
            # Build weight matrix
            n = len(year_data)
            rows, cols, data = [], [], []
            for i in range(n):
                for j in indices[i][1:]:  # skip self
                    rows.append(i); cols.append(j); data.append(1.0)
            w = sparse.csr_matrix((data, (rows, cols)), shape=(n, n))
            print(f"  Distance-based weights (k=5): {n} regions")
        except:
            print(f"  WARNING: Could not build any spatial weights")
    
    for ind in indicators:
        if ind not in year_data.columns:
            print(f"  Skipping {ind} (not in data)")
            continue
        
        values = year_data[ind].fillna(0).values
        if values.std() == 0:
            print(f"  Skipping {ind} (zero variance)")
            continue
        
        ind_res = {'indicator': ind, 'n_regions': int(values.sum() > 0)}
        
        # ── Moran's I ──
        if w is not None and libpysal:
            try:
                moran = Moran(values, w)
                ind_res['morans_i'] = round(float(moran.I), 6)
                ind_res['morans_p'] = round(float(moran.p_sim), 6)
                ind_res['morans_z'] = round(float(moran.z_sim), 4)
                ind_res['morans_ei'] = round(float(moran.EI), 6)
                print(f"  {ind}: Moran's I = {moran.I:.4f}, p = {moran.p_sim:.4f}")
            except Exception as e:
                print(f"  {ind}: Moran's I failed: {e}")
                ind_res['morans_i'] = None
        
        # ── LISA ──
        if w is not None and libpysal:
            try:
                lisa = Moran_Local(values, w, permutations=999)
                clusters = []
                for i in range(len(year_data)):
                    if lisa.p_sim[i] < 0.05:
                        q = lisa.q[i]
                        if q == 1: clusters.append({'region': year_data.iloc[i]['rayon'], 'cluster': 'HH'})
                        elif q == 2: clusters.append({'region': year_data.iloc[i]['rayon'], 'cluster': 'LH'})
                        elif q == 3: clusters.append({'region': year_data.iloc[i]['rayon'], 'cluster': 'LL'})
                        elif q == 4: clusters.append({'region': year_data.iloc[i]['rayon'], 'cluster': 'HL'})
                ind_res['lisa_clusters'] = clusters
                ind_res['lisa_sig_count'] = len(clusters)
                print(f"  {ind}: {len(clusters)} significant LISA clusters")
            except Exception as e:
                print(f"  {ind}: LISA failed: {e}")
        
        # ── Getis-Ord Gi* (hot spots) ──
        if w is not None:
            try:
                from esda.getisord import G_Local
                gi = G_Local(values, w, transform='r')
                gi_z = gi.z_sim
                gi_p = gi.p_sim
                hot_spots = []
                for i in range(len(year_data)):
                    if gi_p[i] < 0.05:
                        htype = 'hot' if gi_z[i] > 0 else 'cold'
                        hot_spots.append({'region': year_data.iloc[i]['rayon'], 'type': htype, 'z_score': round(float(gi_z[i]), 4)})
                ind_res['hot_spots'] = hot_spots
                ind_res['hot_count'] = sum(1 for h in hot_spots if h['type'] == 'hot')
                ind_res['cold_count'] = sum(1 for h in hot_spots if h['type'] == 'cold')
                print(f"  {ind}: {ind_res['hot_count']} hot spots, {ind_res['cold_count']} cold spots")
            except Exception as e:
                print(f"  {ind}: Getis-Ord failed: {e}")
        
        # ── Mean Center & Std Ellipse ──
        try:
            centroids = year_data.geometry.centroid
            coords = np.array([(c.x, c.y) for c in centroids])
            weights = values / values.sum() if values.sum() > 0 else np.ones(len(values))
            
            # Weighted mean center
            mc_x = np.average(coords[:, 0], weights=weights)
            mc_y = np.average(coords[:, 1], weights=weights)
            
            # Standard deviational ellipse
            dx = coords[:, 0] - mc_x
            dy = coords[:, 1] - mc_y
            wsum = weights.sum()
            sxx = np.sum(weights * dx * dx) / wsum
            syy = np.sum(weights * dy * dy) / wsum
            sxy = np.sum(weights * dx * dy) / wsum
            
            # Rotation angle
            theta = 0.5 * math.atan2(2 * sxy, sxx - syy)
            # Standard deviations along axes
            sd_x = math.sqrt(sxx + syy + math.sqrt((sxx - syy)**2 + 4*sxy**2))
            sd_y = math.sqrt(sxx + syy - math.sqrt((sxx - syy)**2 + 4*sxy**2))
            
            ind_res['mean_center'] = {'x': round(float(mc_x), 4), 'y': round(float(mc_y), 4)}
            ind_res['std_ellipse'] = {
                'cx': round(float(mc_x), 4), 'cy': round(float(mc_y), 4),
                'sdx': round(float(sd_x), 4), 'sdy': round(float(sd_y), 4),
                'theta': round(float(theta), 4)
            }
        except Exception as e:
            print(f"  {ind}: Mean center/ellipse failed: {e}")
        
        results['indicators'][ind] = ind_res
    
    return results


# ── Map Generation ──
def make_choropleth(gdf_panel, year, column, title, filename, cmap='YlOrRd'):
    """Generate a QGIS-quality choropleth map."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    if column not in year_data.columns or len(year_data) == 0:
        plt.close()
        return
    
    vmin = year_data[column].quantile(0.02) if column in year_data.columns else 0
    vmax = year_data[column].quantile(0.98) if column in year_data.columns else 1
    if vmin == vmax: vmax = vmin + 0.01
    
    year_data.plot(column=column, ax=ax, cmap=cmap, edgecolor='#334155', linewidth=0.5,
                   legend=True, legend_kwds={'shrink': 0.6, 'label': title}, 
                   vmin=vmin, vmax=vmax, alpha=0.9)
    
    # Add basemap
    if ctx:
        try:
            ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, alpha=0.4)
        except:
            pass
    
    # Labels for major cities
    cities = {'Bakı': (49.867, 40.409), 'Gəncə': (46.360, 40.683), 'Sumqayıt': (49.669, 40.590),
              'Naxçıvan': (45.411, 39.209), 'Lənkəran': (48.851, 38.754), 'Mingəçevir': (47.049, 40.770)}
    try:
        for city, (lon, lat) in cities.items():
            x, y = Point(lon, lat).to_crs('EPSG:3857').coords[0] if hasattr(Point(lon,lat).to_crs, '__call__') else (lon*111320, lat*111320)
            ax.text(x, y, city, fontsize=7, color=TEXT, ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='#0f0f1a', edgecolor='none', alpha=0.7))
    except:
        pass
    
    ax.set_title(f'{title}\n{year} Yılı | {year} Data', fontsize=14, fontweight='bold', color=TEXT, pad=20)
    ax.axis('off')
    
    # Legend styling
    try:
        fig.savefig(os.path.join(MAPS, filename), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
        print(f"  Saved: {filename}")
    except Exception as e:
        print(f"  ERROR saving {filename}: {e}")
    plt.close()


def make_hotspot_map(gdf_panel, year, column, title, filename):
    """Generate Getis-Ord Gi* hot spot map."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    if column not in year_data.columns or len(year_data) == 0:
        plt.close()
        return
    
    values = year_data[column].fillna(0).values
    centroids = year_data.geometry.centroid
    coords = np.array([(c.x, c.y) for c in centroids])
    
    # Simple hot spot calculation (distance-based)
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=5)
    nn.fit(coords)
    distances, indices = nn.kneighbors(coords)
    
    z_scores = np.zeros(len(year_data))
    for i in range(len(year_data)):
        neighbors = [year_data.iloc[j][column] for j in indices[i] if j != i]
        if len(neighbors) > 0 and values.std() > 0:
            local_sum = values[i] + sum(neighbors)
            expected = values.mean() * (len(neighbors) + 1)
            s = values.std() * math.sqrt(len(neighbors) + 1)
            z_scores[i] = (local_sum - expected) / s if s > 0 else 0
    
    year_data['z_score'] = z_scores
    year_data['hotspot_label'] = ''
    year_data['hotspot_color'] = '#333333'
    
    for i in range(len(year_data)):
        z = z_scores[i]
        if z >= 2.58:
            year_data.loc[year_data.index[i], 'hotspot_label'] = 'Hot (99%)'
            year_data.loc[year_data.index[i], 'hotspot_color'] = '#b2182b'
        elif z >= 1.96:
            year_data.loc[year_data.index[i], 'hotspot_label'] = 'Hot (95%)'
            year_data.loc[year_data.index[i], 'hotspot_color'] = '#fddbc7'
        elif z <= -2.58:
            year_data.loc[year_data.index[i], 'hotspot_label'] = 'Cold (99%)'
            year_data.loc[year_data.index[i], 'hotspot_color'] = '#2166ac'
        elif z <= -1.96:
            year_data.loc[year_data.index[i], 'hotspot_label'] = 'Cold (95%)'
            year_data.loc[year_data.index[i], 'hotspot_color'] = '#67a9cf'
        else:
            year_data.loc[year_data.index[i], 'hotspot_label'] = 'Not Sig.'
            year_data.loc[year_data.index[i], 'hotspot_color'] = '#f0f0f0'
    
    year_data.plot(ax=ax, color=year_data['hotspot_color'], edgecolor='#334155', linewidth=0.5)
    
    if ctx:
        try:
            ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, alpha=0.3)
        except:
            pass
    
    ax.set_title(f'Hot Spot Analysis (Getis-Ord Gi*)\n{title} - {year}', fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    # Legend
    legend_elements = [
        mpatches.Patch(color='#b2182b', label='Hot (99%)'),
        mpatches.Patch(color='#fddbc7', label='Hot (95%)'),
        mpatches.Patch(color='#f0f0f0', label='Not Sig.'),
        mpatches.Patch(color='#67a9cf', label='Cold (95%)'),
        mpatches.Patch(color='#2166ac', label='Cold (99%)'),
    ]
    ax.legend(handles=legend_elements, loc='lower left', fontsize=8, framealpha=0.7)
    
    fig.savefig(os.path.join(MAPS, filename), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
    print(f"  Saved: {filename}")
    plt.close()


def make_lisa_map(gdf_panel, year, column, title, filename):
    """Generate LISA cluster map."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    if column not in year_data.columns or len(year_data) == 0:
        plt.close()
        return
    
    values = year_data[column].fillna(0).values
    n = len(values)
    if n == 0 or values.std() == 0:
        plt.close()
        return
    
    # Simple LISA-like calculation
    centroids = year_data.geometry.centroid
    coords = np.array([(c.x, c.y) for c in centroids])
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=5)
    nn.fit(coords)
    distances, indices = nn.kneighbors(coords)
    
    z = (values - values.mean()) / values.std() if values.std() > 0 else np.zeros(n)
    lisa_vals = np.zeros(n)
    for i in range(n):
        neighbors = z[indices[i][1:]]
        lisa_vals[i] = z[i] * np.sum(neighbors)
    
    # Classify
    clusters = np.full(n, 'Not Significant', dtype=object)
    threshold = 1.65  # ~90% confidence
    for i in range(n):
        if abs(lisa_vals[i]) < threshold: continue
        if z[i] > 0 and sum(z[indices[i][1:]]) > 0: clusters[i] = 'HH'
        elif z[i] < 0 and sum(z[indices[i][1:]]) < 0: clusters[i] = 'LL'
        elif z[i] > 0 and sum(z[indices[i][1:]]) < 0: clusters[i] = 'HL'
        else: clusters[i] = 'LH'
    
    year_data['lisa_cluster'] = clusters
    
    lisa_colors = {'HH': '#e74c3c', 'LL': '#3498db', 'HL': '#f39c12', 'LH': '#1abc9c', 'Not Significant': '#2c2c3c'}
    year_data['color'] = year_data['lisa_cluster'].map(lisa_colors)
    
    year_data.plot(ax=ax, color=year_data['color'], edgecolor='#334155', linewidth=0.5)
    
    # Legend
    patches = [mpatches.Patch(color=c, label=l) for l, c in lisa_colors.items()]
    ax.legend(handles=patches, loc='lower left', fontsize=8, framealpha=0.7)
    
    if ctx:
        try:
            ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, alpha=0.3)
        except:
            pass
    
    ax.set_title(f'LISA Cluster Map\n{title} - {year}\nHH=High-High  LL=Low-Low  HL=High-Low  LH=Low-High', 
                 fontsize=12, fontweight='bold', pad=20)
    ax.axis('off')
    
    fig.savefig(os.path.join(MAPS, filename), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
    print(f"  Saved: {filename}")
    plt.close()


def make_kde_map(gdf_panel, year, column, title, filename):
    """Generate Kernel Density Estimation map."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    if column not in year_data.columns or len(year_data) == 0:
        plt.close()
        return
    
    centroids = year_data.geometry.centroid
    coords = np.array([(c.x, c.y) for c in centroids])
    weights = year_data[column].fillna(0).values
    
    from scipy.stats import gaussian_kde
    
    # Remove zeros for log-scale
    valid = weights > 0
    if valid.sum() < 5:
        plt.close()
        return
    
    # Weighted KDE approximation: sample points proportional to weights
    try:
        n_samples = min(5000, len(weights) * 100)
        probs = weights / weights.sum()
        sampled_indices = np.random.choice(len(coords), size=n_samples, p=probs)
        sampled_coords = coords[sampled_indices]
        
        if len(sampled_coords) > 10:
            kde = gaussian_kde(sampled_coords.T)
            
            # Create grid
            xmin, ymin = coords.min(axis=0)
            xmax, ymax = coords.max(axis=0)
            xs, ys = np.meshgrid(np.linspace(xmin, xmax, 100), np.linspace(ymin, ymax, 100))
            grid = np.vstack([xs.ravel(), ys.ravel()])
            
            z = kde(grid).reshape(xs.shape)
            
            ax.imshow(z, extent=[xmin, xmax, ymin, ymax], origin='lower', cmap='hot', alpha=0.7, aspect='auto')
    except Exception as e:
        print(f"  KDE failed for {column}: {e}")
        plt.close()
        return
    
    # Plot boundaries
    year_data.plot(ax=ax, facecolor='none', edgecolor='#334155', linewidth=1)
    
    ax.set_title(f'Kernel Density Estimation\n{title} - {year}', fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')
    
    fig.savefig(os.path.join(MAPS, filename), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
    print(f"  Saved: {filename}")
    plt.close()


def make_bivariate_map(gdf_panel, year, col1, col2, title1, title2, filename):
    """Generate bivariate choropleth map."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    if col1 not in year_data.columns or col2 not in year_data.columns or len(year_data) == 0:
        plt.close()
        return
    
    # Bivariate classification using quantiles
    v1 = year_data[col1].fillna(0).values
    v2 = year_data[col2].fillna(0).values
    
    # 3x3 bivariate scheme
    q1 = np.percentile(v1[v1 > 0], [33.3, 66.7]) if (v1 > 0).sum() > 5 else [v1.mean()/2, v1.mean()]
    q2 = np.percentile(v2[v2 > 0], [33.3, 66.7]) if (v2 > 0).sum() > 5 else [v2.mean()/2, v2.mean()]
    
    biv_colors = {
        (0,0): '#e8e8e8', (0,1): '#b3cde3', (0,2): '#6497b1',
        (1,0): '#fbb4b9', (1,1): '#ccebc5', (1,2): '#7bccc4',
        (2,0): '#e7d4e8', (2,1): '#b8e6b8', (2,2): '#2b8cbe'
    }
    
    def classify_val(v, v_q):
        if v <= v_q[0] if len(v_q) > 0 else 0: return 0
        elif len(v_q) == 1 or v <= v_q[-1] if len(v_q) > 1 else v: return 1
        return 2
    
    colors = []
    for i in range(len(year_data)):
        c1 = min(classify_val(v1[i] if v1[i] > 0 else 0, q1), 2) if v1[i] > 0 else 0
        c2 = min(classify_val(v2[i] if v2[i] > 0 else 0, q2), 2) if v2[i] > 0 else 0
        colors.append(biv_colors.get((c1, c2), '#e8e8e8'))
    
    year_data.plot(ax=ax, color=colors, edgecolor='#334155', linewidth=0.5)
    
    if ctx:
        try:
            ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, alpha=0.3)
        except:
            pass
    
    ax.set_title(f'Bivariate Choropleth\n{title1} (X) × {title2} (Y) - {year}', fontsize=13, fontweight='bold', pad=20)
    ax.axis('off')
    
    fig.savefig(os.path.join(MAPS, filename), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
    print(f"  Saved: {filename}")
    plt.close()


def make_mean_center_map(gdf_panel, year, column, title, filename):
    """Generate map with mean center and std ellipse."""
    from matplotlib.patches import Ellipse
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    if column not in year_data.columns or len(year_data) == 0:
        plt.close()
        return
    
    values = year_data[column].fillna(0).values
    centroids = year_data.geometry.centroid
    coords = np.array([(c.x, c.y) for c in centroids])
    
    if values.sum() == 0:
        plt.close()
        return
    
    weights = values / values.sum()
    
    mc_x = np.average(coords[:, 0], weights=weights)
    mc_y = np.average(coords[:, 1], weights=weights)
    
    dx = coords[:, 0] - mc_x
    dy = coords[:, 1] - mc_y
    wsum = weights.sum()
    sxx = np.sum(weights * dx * dx) / wsum
    syy = np.sum(weights * dy * dy) / wsum
    sxy = np.sum(weights * dx * dy) / wsum
    theta = 0.5 * math.atan2(2 * sxy, sxx - syy)
    sd_x = math.sqrt(abs(sxx + syy + math.sqrt((sxx - syy)**2 + 4*sxy**2)))
    sd_y = math.sqrt(abs(sxx + syy - math.sqrt((sxx - syy)**2 + 4*sxy**2)))
    
    year_data.plot(ax=ax, column=column, cmap='YlOrRd', edgecolor='#334155', linewidth=0.5, alpha=0.8,
                   legend=True, legend_kwds={'shrink': 0.6, 'label': title})
    
    # Mean center
    ax.scatter(mc_x, mc_y, c='#e74c3c', s=100, marker='D', zorder=5, label='Mean Center')
    
    # Std ellipse (1 SD)
    ellipse = Ellipse(xy=(mc_x, mc_y), width=2*sd_x, height=2*sd_y, angle=math.degrees(theta),
                      facecolor='none', edgecolor='#f39c12', linewidth=2, linestyle='--', zorder=4, label='1 Std Dev')
    ax.add_patch(ellipse)
    # 2 SD
    ellipse2 = Ellipse(xy=(mc_x, mc_y), width=4*sd_x, height=4*sd_y, angle=math.degrees(theta),
                       facecolor='none', edgecolor='#f39c12', linewidth=1, linestyle=':', zorder=3, alpha=0.6)
    ax.add_patch(ellipse2)
    
    if ctx:
        try:
            ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, alpha=0.3)
        except:
            pass
    
    ax.legend(loc='lower left', fontsize=8, framealpha=0.7)
    ax.set_title(f'Mean Center & Standard Deviational Ellipse\n{title} - {year}', fontsize=13, fontweight='bold', pad=20)
    ax.axis('off')
    
    fig.savefig(os.path.join(MAPS, filename), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
    print(f"  Saved: {filename}")
    plt.close()


# ── Correlation Analysis ──
def correlation_analysis(gdf_panel, year):
    print("\n=== Correlation Analysis ===")
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    
    num_cols = ['capacity', 'rooms', 'nights', 'nights_domestic', 'nights_foreign',
                'guests', 'guests_domestic', 'guests_foreign', 'revenue', 'expense', 'employees',
                'hotel_density', 'revenue_per_capacity', 'revenue_per_guest', 'expense_per_guest',
                'avg_stay', 'foreign_tourist_ratio', 'profit']
    
    available = [c for c in num_cols if c in year_data.columns]
    corr_df = year_data[available].corr()
    
    # Save
    corr_data = {
        'columns': list(corr_df.columns),
        'matrix': corr_df.round(4).values.tolist(),
        'year': int(year)
    }
    with open(os.path.join(PROC, 'correlation_matrix.json'), 'w') as f:
        json.dump(corr_data, f, indent=2)
    print(f"  Saved correlation matrix ({len(corr_df.columns)}x{len(corr_df.columns)})")
    
    # Top 5 strongest correlations
    pairs = []
    for i in range(len(corr_df.columns)):
        for j in range(i+1, len(corr_df.columns)):
            pairs.append((corr_df.columns[i], corr_df.columns[j], abs(corr_df.iloc[i, j]), corr_df.iloc[i, j]))
    pairs.sort(key=lambda x: x[2], reverse=True)
    
    print(f"  Top 5 strongest correlations:")
    for p in pairs[:5]:
        print(f"    {p[0]} ↔ {p[1]}: r = {p[3]:.4f}")
    
    # Generate correlation heatmap
    fig, ax = plt.subplots(figsize=(14, 12))
    im = ax.imshow(corr_df.values, cmap='RdBu_r', vmin=-1, vmax=1)
    
    ax.set_xticks(range(len(corr_df.columns)))
    ax.set_yticks(range(len(corr_df.columns)))
    ax.set_xticklabels(corr_df.columns, rotation=90, fontsize=7)
    ax.set_yticklabels(corr_df.columns, fontsize=7)
    
    # Add text annotations
    for i in range(len(corr_df.columns)):
        for j in range(len(corr_df.columns)):
            text = ax.text(j, i, f'{corr_df.iloc[i, j]:.2f}', ha='center', va='center', fontsize=5, color='white' if abs(corr_df.iloc[i, j]) > 0.5 else '#cccccc')
    
    plt.colorbar(im, ax=ax, shrink=0.8, label='Pearson Correlation')
    ax.set_title(f'Accommodation Indicators Correlation Matrix\n{year}', fontsize=14, fontweight='bold', pad=20)
    fig.tight_layout()
    fig.savefig(os.path.join(MAPS, 'correlation_heatmap.png'), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
    print(f"  Saved: correlation_heatmap.png")
    plt.close()
    
    # Scatter matrix for top 6
    top_cols = [p[0] for p in pairs[:3]] + [p[1] for p in pairs[:3]]
    top_cols = list(dict.fromkeys(top_cols))[:6]
    
    from pandas.plotting import scatter_matrix
    try:
        result = scatter_matrix(year_data[top_cols], alpha=0.6, figsize=(16, 16), diagonal='kde',
                       color='#3498db', linewidth=0.5)
        # Handle different return types (scalar, array, or tuple)
        if isinstance(result, np.ndarray):
            axes = result
        elif hasattr(result, 'flatten'):
            axes = result
        elif isinstance(result, tuple):
            axes = result[0] if len(result) > 0 else None
        else:
            axes = None
        if axes is not None:
            for ax in np.asarray(axes).flatten():
                try: ax.set_facecolor(BG)
                except: pass
        fig = plt.gcf()
        fig.savefig(os.path.join(MAPS, 'scatter_matrix.png'), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
        print(f"  Saved: scatter_matrix.png")
    except Exception as e:
        print(f"  scatter_matrix failed: {e}")
    plt.close('all')
    
    return corr_data


# ── Tourism Development Index ──
def tourism_development_index(gdf_panel, year):
    print("\n=== Tourism Development Index ===")
    year_data = gdf_panel[gdf_panel['year'] == year].copy()
    
    indicators = ['capacity', 'nights', 'guests', 'revenue', 'employees', 'foreign_tourist_ratio']
    available = [c for c in indicators if c in year_data.columns]
    
    if len(available) < 3:
        print(f"  Not enough indicators available: {available}")
        return None
    
    # Normalize each to 0-1
    tdi_data = pd.DataFrame({'rayon': year_data['rayon']})
    tdi_data['economic_region'] = year_data['economic_region']
    
    for ind in available:
        vals = year_data[ind].fillna(0).values
        vmin, vmax = vals.min(), vals.max()
        if vmax > vmin:
            tdi_data[ind] = (vals - vmin) / (vmax - vmin)
        else:
            tdi_data[ind] = 0.5
    
    # Composite index (equal weight)
    tdi_data['tourism_development_index'] = tdi_data[available].mean(axis=1)
    
    # Normalize final index to 0-1
    tdi_data['tourism_development_index'] = (tdi_data['tourism_development_index'] - tdi_data['tourism_development_index'].min()) / \
                                             (tdi_data['tourism_development_index'].max() - tdi_data['tourism_development_index'].min() + 0.001)
    
    # Save
    result = tdi_data[['rayon', 'economic_region', 'tourism_development_index']].to_dict(orient='records')
    with open(os.path.join(PROC, 'tourism_development_index.json'), 'w') as f:
        json.dump({'year': int(year), 'indicators': available, 'results': result}, f, indent=2)
    print(f"  Saved TDI for {len(result)} rayons")
    print(f"  Top 5: {tdi_data.nlargest(5, 'tourism_development_index')[['rayon', 'tourism_development_index']].to_string()}")
    
    # Generate TDI map
    year_data = year_data.copy()
    tdi_dict = dict(zip(tdi_data['rayon'], tdi_data['tourism_development_index']))
    year_data['tdi'] = year_data['rayon'].map(tdi_dict)
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    year_data.plot(column='tdi', ax=ax, cmap='viridis', edgecolor='#334155', linewidth=0.5,
                   legend=True, legend_kwds={'shrink': 0.6, 'label': 'Tourism Development Index'},
                   vmin=0, vmax=1, alpha=0.9)
    
    if ctx:
        try:
            ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, alpha=0.3)
        except:
            pass
    
    ax.set_title(f'Tourism Development Index (TDI)\nComposite Index of {len(available)} Indicators - {year}', 
                 fontsize=13, fontweight='bold', pad=20)
    ax.axis('off')
    
    fig.savefig(os.path.join(MAPS, 'tourism_development_index.png'), dpi=200, bbox_inches='tight', facecolor=BG, edgecolor='none')
    print(f"  Saved: tourism_development_index.png")
    plt.close()
    
    return tdi_data


# ── Temporal Animation Frames ──
def generate_animation_frames(gdf_panel):
    print("\n=== Spatio-temporal Animation Frames ===")
    
    years = sorted(gdf_panel['year'].unique())
    step = max(1, len(years) // 5)  # Show every ~5 years if spanning many
    
    selected_years = years[::step]
    if years[-1] not in selected_years:
        selected_years.append(years[-1])
    
    for year in selected_years:
        year_data = gdf_panel[gdf_panel['year'] == year].copy()
        if len(year_data) == 0:
            continue
        
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        
        if 'capacity' in year_data.columns:
            vmin = year_data['capacity'].quantile(0.05)
            vmax = year_data['capacity'].quantile(0.95)
            year_data.plot(column='capacity', ax=ax, cmap='YlOrRd', edgecolor='#334155', linewidth=0.5,
                          legend=True, legend_kwds={'shrink': 0.5, 'label': 'Capacity'},
                          vmin=vmin, vmax=vmax)
        
        if ctx:
            try:
                ctx.add_basemap(ax, source=ctx.providers.CartoDB.DarkMatter, alpha=0.3)
            except:
                pass
        
        ax.set_title(f'Hotel Capacity by Rayon\n{year}', fontsize=16, fontweight='bold', color=TEXT, pad=20)
        ax.axis('off')
        
        fig.savefig(os.path.join(FRAMES, f'capacity_{year}.png'), dpi=150, bbox_inches='tight', facecolor=BG, edgecolor='none')
        plt.close()
        print(f"  Frame: capacity_{year}.png")
    
    # Create animated GIF
    try:
        from PIL import Image
        frames = []
        for year in selected_years:
            fpath = os.path.join(FRAMES, f'capacity_{year}.png')
            if os.path.exists(fpath):
                frames.append(Image.open(fpath))
        
        if frames:
            frames[0].save(os.path.join(MAPS, 'temporal_animation.gif'),
                          save_all=True, append_images=frames[1:],
                          duration=1000, loop=0, optimize=False)
            print(f"  Saved: temporal_animation.gif ({len(frames)} frames)")
    except ImportError:
        print("  PIL not available, skipping GIF creation")
    except Exception as e:
        print(f"  GIF creation failed: {e}")


# ── Main ──
def main():
    print("=" * 70)
    print("ACCOMMODATION SPATIAL ANALYSIS & MAP GENERATION")
    print("=" * 70)
    
    panel, gdf_panel, best_year, latest_year = load_data()
    
    # Use latest year with data
    analysis_year = latest_year if latest_year in gdf_panel['year'].values else best_year
    
    # 1. Spatial analysis
    spatial_results = run_spatial_analysis(gdf_panel, analysis_year)
    
    # Save spatial results
    with open(os.path.join(PROC, 'spatial_analysis.json'), 'w') as f:
        json.dump(spatial_results, f, indent=2)
    print(f"\n  Saved spatial_analysis.json")
    
    # 2. Generate all maps
    print("\n=== Generating Maps ===")
    
    indicators_map = [
        ('capacity', 'Hotel Capacity (Birdəfəlik Tutum)', 'YlOrRd'),
        ('rooms', 'Room Count (Nömrə Sayı)', 'YlOrRd'),
        ('nights', 'Overnight Stays (Gecələmə)', 'OrRd'),
        ('guests', 'Total Guests (Yerləşdirilən)', 'RdPu'),
        ('revenue', 'Revenue (Gəlir)', 'Greens'),
        ('expense', 'Expense (Xərc)', 'Oranges'),
        ('employees', 'Employment (İşçilər)', 'BuPu'),
        ('hotel_density', 'Hotel Density (Otel Sıxlığı)', 'YlOrRd'),
        ('revenue_per_capacity', 'Revenue per Capacity (Tutum başına Gəlir)', 'Greens'),
        ('foreign_tourist_ratio', 'Foreign Tourist Ratio (Xarici Turist Oranı)', 'RdYlBu'),
        ('avg_stay', 'Average Stay (Ortalama Gecələmə)', 'Purples'),
        ('profit', 'Profit (Kâr)', 'RdYlGn'),
    ]
    
    for col, title, cmap in indicators_map:
        safe_name = col.replace('.', '_').replace('-', '_')
        
        # Choropleth
        make_choropleth(gdf_panel, analysis_year, col, title, f'choropleth_{safe_name}.png', cmap)
        
        # Hot Spot
        if col in ['capacity', 'nights', 'guests', 'revenue']:
            make_hotspot_map(gdf_panel, analysis_year, col, title, f'hot_spot_{safe_name}.png')
            make_lisa_map(gdf_panel, analysis_year, col, title, f'lisa_cluster_{safe_name}.png')
            make_kde_map(gdf_panel, analysis_year, col, title, f'kde_{safe_name}.png')
            make_mean_center_map(gdf_panel, analysis_year, col, title, f'mean_center_{safe_name}.png')
    
    # Bivariate maps
    make_bivariate_map(gdf_panel, analysis_year, 'hotel_density', 'revenue', 
                       'Hotel Density', 'Revenue', 'bivariate_hotel_density_revenue.png')
    make_bivariate_map(gdf_panel, analysis_year, 'capacity', 'foreign_tourist_ratio',
                       'Capacity', 'Foreign Tourist Ratio', 'bivariate_capacity_foreign_ratio.png')
    
    # 3. Correlation analysis
    correlation_analysis(gdf_panel, analysis_year)
    
    # 4. Tourism Development Index
    tourism_development_index(gdf_panel, analysis_year)
    
    # 5. Animation frames
    generate_animation_frames(gdf_panel)
    
    print("\n" + "=" * 70)
    print("ALL ANALYSIS AND MAPS COMPLETE")
    print(f"  Maps saved to: {MAPS}")
    print(f"  Data saved to: {PROC}")
    print("=" * 70)


if __name__ == '__main__':
    main()
