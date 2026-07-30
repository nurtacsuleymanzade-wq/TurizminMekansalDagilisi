#!/usr/bin/env python3
"""
ML Models for Tourism Spatial Distribution Analysis
SAR (ML_Lag), Random Forest, XGBoost
"""
import os
import json
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error
import xgboost as xgb

warnings.filterwarnings('ignore')

# ── Config ──────────────────────────────────────────────────────────────
DATA_PATH = 'data/processed/rayon_feature_matrix.csv'
OUT_DIR = 'models'
os.makedirs(OUT_DIR, exist_ok=True)

# ── Load Data ───────────────────────────────────────────────────────────
df = pd.read_csv(DATA_PATH)
print(f"Loaded {df.shape[0]} rayons, {df.shape[1]} columns")

target_col = 'total'
feature_cols = [c for c in df.columns if c not in ('rayon', 'lon', 'lat', target_col)]
geo_cols = ['lon', 'lat']

print(f"Target: {target_col}")
print(f"Features ({len(feature_cols)}): {feature_cols}")

X = df[feature_cols].values
y = df[target_col].values
coords = df[geo_cols].values
rayon_names = df['rayon'].values

# NOTE: Data is extremely sparse. Only 'Otel' has meaningful variance
# (12 non-zero). All other features have only 1 non-zero each.
# For linear spatial models (SAR), use only Otel + constant.
# For tree-based models, keep all features.
sar_feature_idx = feature_cols.index('Otel')
X_sar = X[:, [sar_feature_idx]]  # just Otel
print(f"SAR feature: ['Otel'] only (others too sparse)")

# Split
X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
    X, y, np.arange(len(y)), test_size=0.2, random_state=42
)
print(f"Train: {len(y_train)}, Test: {len(y_test)}")

# ── 1. SAR (Spatial AutoRegressive - ML_Lag) ──────────────────────────
print("\n--- SAR (ML_Lag with Otel feature) ---")
sar_success = False
sar_pred = np.zeros(len(y))
sar_residuals = np.zeros(len(y))

try:
    from libpysal.weights import DistanceBand
    import spreg

    # Use distance band for spatial weights
    w = DistanceBand.from_array(coords, threshold=1.5, binary=True)
    w.transform = 'r'
    
    # ML_Lag with just 1 feature
    sar = spreg.ML_Lag(y.reshape(-1, 1), X_sar, w=w, method='full')
    sar_success = True
    
    rho = sar.rho
    if hasattr(rho, '__iter__') and not isinstance(rho, (int, float)):
        rho = float(rho[0])
    else:
        rho = float(rho)
    
    # spreg v1.9 uses predy (not predy_flipped)
    sar_pred_y = sar.predy
    if isinstance(sar_pred_y, (list, tuple)):
        sar_pred_y = np.array(sar_pred_y)
    if sar_pred_y.ndim == 2:
        sar_pred_y = sar_pred_y[:, 0] if sar_pred_y.shape[1] > 1 else sar_pred_y.flatten()
    
    sar_residuals = sar.u
    if isinstance(sar_residuals, (list, tuple)):
        sar_residuals = np.array(sar_residuals)
    sar_residuals = sar_residuals.flatten()
    
    sar_r2 = r2_score(y, sar_pred_y)
    sar_rmse = np.sqrt(mean_squared_error(y, sar_pred_y))
    
    # log_likelihood might be log_likelihood or ll
    ll = getattr(sar, 'log_likelihood', getattr(sar, 'll', 0))
    
    print(f"  ρ (spatial lag): {rho:.4f}")
    print(f"  R² (in-sample): {sar_r2:.4f}")
    print(f"  RMSE (in-sample): {sar_rmse:.4f}")
    print(f"  Log-likelihood: {ll:.2f}")
    
    sar_results = {
        'model': 'ML_Lag (Otel)',
        'rho': rho,
        'r2': round(sar_r2, 4),
        'rmse': round(sar_rmse, 4),
        'log_likelihood': float(ll) if ll else 0,
        'predictions': sar_pred_y.tolist(),
        'residuals': sar_residuals.tolist()
    }
    sar_pred = sar_pred_y

except Exception as e:
    print(f"  ML_Lag failed: {e}")
    print("  Falling back to OLS")
    try:
        import statsmodels.api as sm
        Xc = sm.add_constant(X_sar)
        ols = sm.OLS(y, Xc).fit()
        sar_pred = ols.predict(Xc)
        sar_residuals = ols.resid
        sar_r2 = r2_score(y, sar_pred)
        sar_rmse = np.sqrt(mean_squared_error(y, sar_pred))
        rho = 0.0
        sar_results = {
            'model': 'OLS (SAR fallback)',
            'r2': round(sar_r2, 4),
            'rmse': round(sar_rmse, 4),
            'predictions': sar_pred.tolist(),
            'residuals': sar_residuals.tolist()
        }
        print(f"  OLS R²: {sar_r2:.4f}, RMSE: {sar_rmse:.4f}")
    except Exception as e2:
        print(f"  OLS failed: {e2}")
        sar_pred = np.full(len(y), np.mean(y))
        sar_residuals = y - sar_pred
        sar_results = {'model': 'Mean', 'r2': 0.0, 'rmse': float(np.sqrt(mean_squared_error(y, sar_pred))), 'predictions': sar_pred.tolist(), 'residuals': sar_residuals.tolist()}

# ── 2. Random Forest ──────────────────────────────────────────────────
print("\n--- Random Forest ---")
rf = RandomForestRegressor(n_estimators=200, max_depth=12, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)

rf_pred_train = rf.predict(X_train)
rf_pred_test = rf.predict(X_test)
rf_r2_train = r2_score(y_train, rf_pred_train)
rf_rmse_train = np.sqrt(mean_squared_error(y_train, rf_pred_train))
rf_r2_test = r2_score(y_test, rf_pred_test)
rf_rmse_test = np.sqrt(mean_squared_error(y_test, rf_pred_test))
rf_pred_full = rf.predict(X)

print(f"  Train R²: {rf_r2_train:.4f}, RMSE: {rf_rmse_train:.4f}")
print(f"  Test  R²: {rf_r2_test:.4f}, RMSE: {rf_rmse_test:.4f}")

rf_imp = pd.DataFrame({
    'feature': feature_cols,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)
rf_imp.to_csv(f'{OUT_DIR}/rf_feature_importance.csv', index=False)
print(f"  Top features:\n{rf_imp.head(5).to_string(index=False)}")

rf_results = {
    'r2_train': round(rf_r2_train, 4),
    'rmse_train': round(rf_rmse_train, 4),
    'r2_test': round(rf_r2_test, 4),
    'rmse_test': round(rf_rmse_test, 4),
    'predictions': rf_pred_full.tolist()
}

# ── 3. XGBoost ────────────────────────────────────────────────────────
print("\n--- XGBoost ---")
xgb_model = xgb.XGBRegressor(
    n_estimators=200, max_depth=6, learning_rate=0.1,
    random_state=42, n_jobs=-1, verbosity=0
)
xgb_model.fit(X_train, y_train)

xgb_pred_train = xgb_model.predict(X_train)
xgb_pred_test = xgb_model.predict(X_test)
xgb_r2_train = r2_score(y_train, xgb_pred_train)
xgb_rmse_train = np.sqrt(mean_squared_error(y_train, xgb_pred_train))
xgb_r2_test = r2_score(y_test, xgb_pred_test)
xgb_rmse_test = np.sqrt(mean_squared_error(y_test, xgb_pred_test))
xgb_pred_full = xgb_model.predict(X)

print(f"  Train R²: {xgb_r2_train:.4f}, RMSE: {xgb_rmse_train:.4f}")
print(f"  Test  R²: {xgb_r2_test:.4f}, RMSE: {xgb_rmse_test:.4f}")

xgb_imp = pd.DataFrame({
    'feature': feature_cols,
    'importance': xgb_model.feature_importances_
}).sort_values('importance', ascending=False)
xgb_imp.to_csv(f'{OUT_DIR}/xgb_feature_importance.csv', index=False)
print(f"  Top features:\n{xgb_imp.head(5).to_string(index=False)}")

xgb_results = {
    'r2_train': round(xgb_r2_train, 4),
    'rmse_train': round(xgb_rmse_train, 4),
    'r2_test': round(xgb_r2_test, 4),
    'rmse_test': round(xgb_rmse_test, 4),
    'predictions': xgb_pred_full.tolist()
}

# ── Save Comparison ───────────────────────────────────────────────────
comparison = {
    'sar': sar_results,
    'random_forest': rf_results,
    'xgboost': xgb_results,
    'feature_cols': feature_cols,
    'n_samples': len(y)
}

with open(f'{OUT_DIR}/model_comparison.json', 'w') as f:
    json.dump(comparison, f, indent=2, ensure_ascii=False)

# ── Save All Predictions ──────────────────────────────────────────────
pred_df = pd.DataFrame({
    'rayon': rayon_names,
    'actual': y,
    'lon': coords[:, 0],
    'lat': coords[:, 1],
    'sar_pred': sar_pred,
    'rf_pred': rf_pred_full,
    'xgb_pred': xgb_pred_full,
    'sar_residual': sar_residuals
})
pred_df.to_csv(f'{OUT_DIR}/all_predictions.csv', index=False)
print(f"\nSaved: {OUT_DIR}/all_predictions.csv")

sar_pred_df = pred_df[['rayon', 'actual', 'sar_pred', 'sar_residual', 'lon', 'lat']].copy()
sar_pred_df.to_csv(f'{OUT_DIR}/sar_predictions.csv', index=False)
print(f"Saved: {OUT_DIR}/sar_predictions.csv")

print("\n✅ Model training complete!")
print(f"SAR ({sar_results.get('model', '?')}): R²={sar_results.get('r2', 'N/A')}")
print(f"RF:    R²={rf_r2_test:.4f}")
print(f"XGBoost: R²={xgb_r2_test:.4f}")
