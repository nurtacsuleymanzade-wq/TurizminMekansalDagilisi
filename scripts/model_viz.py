#!/usr/bin/env python3
"""
Model visualization: feature importance, model comparison charts, GeoJSON outputs
"""
import os
import json
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
os.environ['MPLBACKEND'] = 'Agg'

import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
from matplotlib.colors import to_rgba

OUT_DIR = 'models'
DATA_DIR = 'data/processed'
FEATURE_MATRIX = f'{DATA_DIR}/rayon_feature_matrix.csv'
COMPARISON = f'{OUT_DIR}/model_comparison.json'
ALL_PREDS = f'{OUT_DIR}/all_predictions.csv'

# Colors
BLUE = '#3498db'
GREEN = '#2ecc71'
RED = '#e74c3c'
DARK = '#1a1a2e'
SURFACE = '#16213e'
BORDER = '#2a2a4a'
TEXT = '#e0e0e0'
TEXT_MUTED = '#95a5a6'

# ── Style ───────────────────────────────────────────────────────────────
plt.rcParams.update({
    'figure.facecolor': DARK,
    'axes.facecolor': SURFACE,
    'axes.edgecolor': BORDER,
    'axes.labelcolor': TEXT,
    'axes.titlecolor': TEXT,
    'xtick.color': TEXT_MUTED,
    'ytick.color': TEXT_MUTED,
    'text.color': TEXT,
    'legend.facecolor': SURFACE,
    'legend.edgecolor': BORDER,
    'legend.labelcolor': TEXT,
})

# ── Load Data ───────────────────────────────────────────────────────────
df = pd.read_csv(FEATURE_MATRIX)
feature_cols = [c for c in df.columns if c not in ('rayon', 'lon', 'lat', 'total')]

with open(COMPARISON) as f:
    comp = json.load(f)

pred_df = pd.read_csv(ALL_PREDS)
print(f"Loaded {len(pred_df)} predictions")

# ── 1. Feature Importance (RF) ────────────────────────────────────────
print("\n--- Feature Importance Chart ---")
rf_imp = pd.read_csv(f'{OUT_DIR}/rf_feature_importance.csv')
rf_imp = rf_imp.sort_values('importance', ascending=True).tail(15)

fig, ax = plt.subplots(figsize=(10, 7))
colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(rf_imp)))
bars = ax.barh(range(len(rf_imp)), rf_imp['importance'].values, color=colors, edgecolor=BORDER, linewidth=0.5)
ax.set_yticks(range(len(rf_imp)))
ax.set_yticklabels(rf_imp['feature'].values, fontsize=11)
ax.set_xlabel('Önem Skoru (Feature Importance)', fontsize=12, color=TEXT)
ax.set_title('Random Forest — Değişken Önem Sıralaması (Top 15)', fontsize=14, fontweight='bold', pad=15)

# Value labels on bars
for i, (bar, val) in enumerate(zip(bars, rf_imp['importance'].values)):
    ax.text(val + 0.002, bar.get_y() + bar.get_height()/2,
            f'{val:.3f}', va='center', fontsize=9, color=TEXT_MUTED)

ax.set_xlim(0, rf_imp['importance'].max() * 1.15)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.savefig(f'{OUT_DIR}/feature_importance.png', dpi=150, bbox_inches='tight',
            facecolor=DARK, edgecolor='none')
print(f"  Saved: {OUT_DIR}/feature_importance.png")

# ── 2. Model Comparison (R² + RMSE) ──────────────────────────────────
print("\n--- Model Comparison Chart ---")
sar_r2 = comp['sar'].get('r2', 0)
sar_rmse = comp['sar'].get('rmse', 0)
rf_r2 = comp['random_forest'].get('r2_test', 0)
rf_rmse = comp['random_forest'].get('rmse_test', 0)
xgb_r2 = comp['xgboost'].get('r2_test', 0)
xgb_rmse = comp['xgboost'].get('rmse_test', 0)

# For SAR we use in-sample (since it doesn't do train/test split)
sar_label = 'SAR (ML_Lag)\n(in-sample)'
rf_label = 'Random Forest\n(test)'
xgb_label = 'XGBoost\n(test)'
labels = [sar_label, rf_label, xgb_label]
r2_vals = [sar_r2, rf_r2, xgb_r2]
rmse_vals = [sar_rmse, rf_rmse, xgb_rmse]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# R² bar chart
bar_colors_r2 = [BLUE, GREEN, RED]
bars1 = ax1.bar(range(3), r2_vals, color=bar_colors_r2, width=0.55, edgecolor=BORDER, linewidth=0.5)
ax1.set_xticks(range(3))
ax1.set_xticklabels(labels, fontsize=10)
ax1.set_ylabel('R² Skoru', fontsize=12)
ax1.set_title('Model Performansı — R²', fontsize=14, fontweight='bold', pad=15)
ax1.set_ylim(0, max(r2_vals) * 1.25 + 0.05)
for bar, val in zip(bars1, r2_vals):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
             f'{val:.3f}', ha='center', va='bottom', fontsize=11, fontweight='bold', color=TEXT)
ax1.axhline(y=0.8, color=GREEN, linestyle='--', linewidth=0.8, alpha=0.5, label='0.8 eşiği')
ax1.legend(fontsize=9, loc='lower right')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# RMSE bar chart
bar_colors_rmse = [BLUE, GREEN, RED]
bars2 = ax2.bar(range(3), rmse_vals, color=bar_colors_rmse, width=0.55, edgecolor=BORDER, linewidth=0.5)
ax2.set_xticks(range(3))
ax2.set_xticklabels(labels, fontsize=10)
ax2.set_ylabel('RMSE (Kök Ortalama Kare Hata)', fontsize=12)
ax2.set_title('Model Performansı — RMSE', fontsize=14, fontweight='bold', pad=15)
ax2.set_ylim(0, max(rmse_vals) * 1.25 + 2)
for bar, val in zip(bars2, rmse_vals):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
             f'{val:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold', color=TEXT)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(f'{OUT_DIR}/model_comparison.png', dpi=150, bbox_inches='tight',
            facecolor=DARK, edgecolor='none')
print(f"  Saved: {OUT_DIR}/model_comparison.png")

# ── 3. Prediction GeoJSON ─────────────────────────────────────────────
print("\n--- Prediction GeoJSON ---")
features = []
for _, row in pred_df.iterrows():
    features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [float(row['lon']), float(row['lat'])]
        },
        'properties': {
            'rayon': row['rayon'],
            'actual': int(row['actual']),
            'sar_predicted': round(float(row['sar_pred']), 2),
            'rf_predicted': round(float(row['rf_pred']), 2),
            'xgb_predicted': round(float(row['xgb_pred']), 2),
            'sar_residual': round(float(row['sar_residual']), 2)
        }
    })

geojson = {
    'type': 'FeatureCollection',
    'features': features,
    'metadata': {
        'title': 'Turizm Mekansal Model Tahminleri',
        'description': 'SAR, RF, XGBoost modelleri ile rayon bazında turizm POI tahminleri',
        'model_r2': {
            'sar': comp['sar'].get('r2', 0),
            'rf_test': comp['random_forest'].get('r2_test', 0),
            'xgb_test': comp['xgboost'].get('r2_test', 0)
        }
    }
}

with open(f'{OUT_DIR}/prediction_geojson.json', 'w', encoding='utf-8') as f:
    json.dump(geojson, f, indent=2, ensure_ascii=False)
print(f"  Saved: {OUT_DIR}/prediction_geojson.json ({len(features)} features)")

# ── 4. SAR Residual Map GeoJSON ──────────────────────────────────────
print("\n--- SAR Residual GeoJSON ---")
resid_features = []
for _, row in pred_df.iterrows():
    resid_features.append({
        'type': 'Feature',
        'geometry': {
            'type': 'Point',
            'coordinates': [float(row['lon']), float(row['lat'])]
        },
        'properties': {
            'rayon': row['rayon'],
            'actual': int(row['actual']),
            'predicted': round(float(row['sar_pred']), 2),
            'residual': round(float(row['sar_residual']), 2),
            'abs_residual': round(abs(float(row['sar_residual'])), 2)
        }
    })

resid_geojson = {
    'type': 'FeatureCollection',
    'features': resid_features,
    'metadata': {
        'title': 'SAR Model Artıkları',
        'description': 'SAR (ML_Lag) modeli artık haritası. Pozitif: model düşük tahmin etti, Negatif: model yüksek tahmin etti.',
        'model': 'ML_Lag',
        'rho': comp['sar'].get('rho', 0)
    }
}

with open(f'{OUT_DIR}/sar_residual_map.json', 'w', encoding='utf-8') as f:
    json.dump(resid_geojson, f, indent=2, ensure_ascii=False)
print(f"  Saved: {OUT_DIR}/sar_residual_map.json ({len(resid_features)} features)")

print("\n✅ Visualization complete!")
print(f"  PNG files: feature_importance.png, model_comparison.png")
print(f"  GeoJSON files: prediction_geojson.json, sar_residual_map.json")
