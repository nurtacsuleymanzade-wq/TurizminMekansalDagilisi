#!/usr/bin/env python3
"""
Accommodation Statistics Data Pipeline
Parses all 34+4 AzStat XLS files into unified CSVs + derived indicators + regional panel.
"""
import os, sys, json, csv, re, math
import xlrd
import pandas as pd
import numpy as np
import geopandas as gpd
from itertools import chain

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "statistics")
PROC = os.path.join(BASE, "data", "processed", "accommodation")
GEO = os.path.join(BASE, "data", "geojson")
os.makedirs(PROC, exist_ok=True)

# ── Azerbaijani number parser ──
def parse_az_number(s):
    if s is None: return None
    if isinstance(s, (int, float)):
        return float(s) if np.isfinite(s) else None
    s = str(s).strip()
    if not s or s in ('...', '-', '—', '–', '', '.'): return None
    s = s.replace('\xa0', ' ').replace('\u00a0', ' ').replace(',', '.').replace(' ', '')
    try: return float(s)
    except: return None

def parse_header_years(row, start_col=1):
    years = {}
    for c in range(start_col, min(len(row), 30)):
        val = row[c]
        if isinstance(val, (int, float)):
            if val == int(val) and 1995 <= int(val) <= 2030:
                years[c] = int(val)
        elif isinstance(val, str):
            v = val.strip()
            if v.isdigit() and len(v) == 4 and 1995 <= int(v) <= 2030:
                years[c] = int(v)
    return years

# ── 1. Basic indicators (003_1.xls) ──
def extract_hotel_basic():
    print("\n=== Hotel Basic Indicators (003_1.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_1.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    print(f"  Years: {list(years.values())}")
    
    row_map = {
        4: 'hotel_count', 6: 'capacity', 7: 'rooms',
        8: 'guests_total', 10: 'guests_domestic', 11: 'guests_foreign',
        12: 'nights_total', 14: 'nights_domestic', 15: 'nights_foreign',
        16: 'employees', 17: 'revenue', 18: 'expense', 19: 'taxes'
    }
    
    records = []
    for row_idx, label in row_map.items():
        for c, year in years.items():
            val = parse_az_number(ws.cell(row_idx, c).value)
            if val is not None:
                records.append({'year': year, 'indicator': label, 'value': val})
    
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'hotel_basic_indicators.csv'), index=False)
    print(f"  Saved {len(df)} records")
    return df

# ── 2. Hotel by ownership count (003_2.xls) ──
def extract_hotel_ownership_count():
    print("\n=== Hotel By Ownership Count (003_2.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_2.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    print(f"  Years: {list(years.values())}")
    
    row_map = {4: 'total', 6: 'state', 7: 'private', 8: 'foreign', 9: 'joint'}
    records = []
    for row_idx, label in row_map.items():
        for c, year in years.items():
            val = parse_az_number(ws.cell(row_idx, c).value)
            if val is not None:
                records.append({'year': year, 'ownership': label, 'hotel_count': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'hotel_by_ownership_count.csv'), index=False)
    print(f"  Saved {len(df)} records")
    return df

# ── 3. Hotel by ownership capacity (003_3.xls) ──
def extract_ownership_capacity():
    print("\n=== Hotel By Ownership Capacity (003_3.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_3.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    row_map = {4: 'total', 6: 'state', 7: 'private', 8: 'foreign', 9: 'joint'}
    records = []
    for row_idx, label in row_map.items():
        for c, year in years.items():
            val = parse_az_number(ws.cell(row_idx, c).value)
            if val is not None:
                records.append({'year': year, 'ownership': label, 'capacity': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'hotel_by_ownership_capacity.csv'), index=False)
    print(f"  Saved {len(df)} records")
    return df

# ── 4. Hotel stays by ownership (003_4.xls) ──
def extract_stays_ownership():
    print("\n=== Hotel Stays By Ownership (003_4.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_4.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    row_map = {4: 'total', 6: 'state', 7: 'private', 8: 'foreign', 9: 'joint'}
    records = []
    for row_idx, label in row_map.items():
        for c, year in years.items():
            val = parse_az_number(ws.cell(row_idx, c).value)
            if val is not None:
                records.append({'year': year, 'ownership': label, 'guests': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'hotel_stays_by_ownership.csv'), index=False)
    print(f"  Saved {len(df)} records")
    return df

# ── 5. Hotel employees (003_5.xls) ──
def extract_employees():
    print("\n=== Hotel Employees (003_5.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_5.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    row_map = {4: 'total', 6: 'state', 7: 'private', 8: 'foreign', 9: 'joint'}
    records = []
    for row_idx, label in row_map.items():
        for c, year in years.items():
            val = parse_az_number(ws.cell(row_idx, c).value)
            if val is not None:
                records.append({'year': year, 'ownership': label, 'employees': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'hotel_employees.csv'), index=False)
    print(f"  Saved {len(df)} records")
    return df

# ── 6. Hotel revenue/expense (003_6.xls) ──
def extract_revenue_expense():
    print("\n=== Hotel Revenue/Expense (003_6.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_6.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    row_map = {4: 'revenue_total', 6: 'revenue_room', 7: 'revenue_food', 8: 'revenue_other',
               10: 'expense_total', 12: 'expense_material', 13: 'expense_labour', 14: 'expense_depreciation', 15: 'expense_other'}
    records = []
    for row_idx, label in row_map.items():
        for c, year in years.items():
            val = parse_az_number(ws.cell(row_idx, c).value)
            if val is not None:
                records.append({'year': year, 'indicator': label, 'value': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'hotel_revenue_expense.csv'), index=False)
    print(f"  Saved {len(df)} records")
    return df

# ── 7. Revenue/expense by ownership (003_7.xls) ──
def extract_rev_exp_ownership():
    print("\n=== Revenue/Expense By Ownership (003_7.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_7.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    records = []
    # Row layout: 4=total rev, 5=state rev, 6=private rev, 7=foreign rev, 8=joint rev
    # 10=total exp, 11=state exp, 12=private exp, 13=foreign exp, 14=joint exp
    for row_idx, label in [(4,'total'),(5,'state'),(6,'private'),(7,'foreign'),(8,'joint')]:
        for c, year in years.items():
            val = parse_az_number(ws.cell(row_idx, c).value)
            if val is not None:
                records.append({'year': year, 'ownership': label, 'type': 'revenue', 'value': val})
    for row_idx, label in [(10,'total'),(11,'state'),(12,'private'),(13,'foreign'),(14,'joint')]:
        for c, year in years.items():
            val = parse_az_number(ws.cell(row_idx, c).value)
            if val is not None:
                records.append({'year': year, 'ownership': label, 'type': 'expense', 'value': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'hotel_revenue_expense_by_ownership.csv'), index=False)
    print(f"  Saved {len(df)} records")
    return df

# ── 8. Foreigner nights by year (003_8.xls) ──
def extract_foreigner_nights():
    print("\n=== Foreigner Nights By Country (003_8.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_8.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    records = []
    for r in range(4, ws.nrows):
        label = str(ws.cell(r, 0).value).strip() + str(ws.cell(r, 1).value).strip()
        label = label.strip()
        if not label or label in ('', 'o cümlədən ölkələr  üzrə:', 'o cümlədən ölkələr üzrə:'):
            continue
        for c, year in years.items():
            val = parse_az_number(ws.cell(r, c).value)
            if val is not None:
                records.append({'country': label, 'year': year, 'nights': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'foreigner_nights_by_year.csv'), index=False)
    print(f"  Saved {len(df)} records from {df['country'].nunique()} countries")
    return df

# ── 9. Foreigner country stays (003_9.xls) ──
def extract_foreigner_stays():
    print("\n=== Foreigner Stays By Country (003_9.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_9.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    records = []
    for r in range(4, ws.nrows):
        label = str(ws.cell(r, 0).value).strip() + str(ws.cell(r, 1).value).strip()
        label = label.strip()
        if not label or label in ('', 'o cümlədən ölkələr  üzrə:', 'o cümlədən ölkələr üzrə:'):
            continue
        for c, year in years.items():
            val = parse_az_number(ws.cell(r, c).value)
            if val is not None:
                records.append({'country': label, 'year': year, 'guests': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'foreigner_country_stays.csv'), index=False)
    print(f"  Saved {len(df)} records from {df['country'].nunique()} countries")
    return df

# ── 10. Foreigner service value (003_10.xls) ──
def extract_foreigner_service():
    print("\n=== Foreigner Service Value (003_10.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "003_hotel", "003_10.xls"))
    ws = wb.sheet_by_index(0)
    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    records = []
    for r in range(4, ws.nrows):
        label = str(ws.cell(r, 0).value).strip() + str(ws.cell(r, 1).value).strip()
        label = label.strip()
        if not label or label in ('', 'o cümlədən ölkələr  üzrə:', 'o cümlədən ölkələr üzrə:'):
            continue
        for c, year in years.items():
            val = parse_az_number(ws.cell(r, c).value)
            if val is not None:
                records.append({'country': label, 'year': year, 'service_value': val})
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'foreigner_service_value.csv'), index=False)
    print(f"  Saved {len(df)} records from {df['country'].nunique()} countries")
    return df


# ════════════════════════════════════════════════════
# REGIONAL DATA (005 series)
# ════════════════════════════════════════════════════

REGIONAL_COLUMNS_005 = [
    ('capacity', '005_1.xls', 'Birdəfəlik tutum'),
    ('rooms', '005_2.xls', 'Nömrələrin sayı'),
    ('nights', '005_3.xls', 'Gecələmələrin sayı'),
    ('nights_domestic', '005_4.xls', 'Gecələmələr (ölkə vətəndaşları)'),
    ('nights_foreign', '005_5.xls', 'Gecələmələr (xarici vətəndaşlar)'),
    ('guests', '005_6.xls', 'Yerləşdirilmiş şəxslər'),
    ('guests_domestic', '005_7.xls', 'Yerləşdirilmiş şəxslər (ölkə vətəndaşları)'),
    ('guests_foreign', '005_8.xls', 'Yerləşdirilmiş şəxslər (xarici vətəndaşlar)'),
    ('revenue', '005_9.xls', 'Gəlirlər'),
    ('expense', '005_10.xls', 'Xərclər'),
    ('employees', '005_11.xls', 'İşçilər'),
]

def extract_regional_all():
    """Parse all 005_*.xls files into a unified regional panel."""
    print("\n=== Extracting All Regional Data (005_1 through 005_11) ===")
    
    all_data = {}
    econ_regions = ("Azərbaycan", "Bakı", "Naxçıvan", "Abşeron", "Sumqayıt", 
                    "Dağlıq Şirvan", "Gəncə", "Qarabağ", "Qazax", "Quba",
                    "Lənkəran", "Aran", "Mil", "Naxçıvan", "Şəki", "Zəngəzur")
    
    for ind_name, fname, label in REGIONAL_COLUMNS_005:
        path = os.path.join(RAW, "005_regional", fname)
        try:
            wb = xlrd.open_workbook(path)
        except:
            print(f"  WARNING: Cannot open {fname}")
            continue
        ws = wb.sheet_by_index(0)
        
        # Find year row (row 4 in most files, but 005_9/10 have different layout)
        year_row_idx = None
        for r in range(min(ws.nrows, 10)):
            row_vals = [ws.cell(r, c).value for c in range(ws.ncols)]
            years = parse_header_years(row_vals)
            if years:
                year_row_idx = r
                break
        
        if year_row_idx is None:
            print(f"  WARNING: No year row found in {fname}")
            continue
        
        years = parse_header_years([ws.cell(year_row_idx, c).value for c in range(ws.ncols)])
        
        # Find data start row (just after year row + header row for indicator name)
        data_start = year_row_idx + 1
        
        region_records = []
        for r in range(data_start, ws.nrows):
            raw_name = str(ws.cell(r, 1).value).strip() if ws.ncols > 1 else ''
            if not raw_name or raw_name in ('о cümlədən:', '', 'o cümlədən:'):
                continue
            # Skip total row
            if 'Respublikası' in raw_name or 'Azərbaycan' == raw_name:
                continue
            # Normalize name
            name = raw_name.replace('\\n', ' ').replace('\n', ' ').strip()
            
            for c, year in years.items():
                val = parse_az_number(ws.cell(r, c).value)
                if val is not None:
                    region_records.append({'rayon': name, 'year': year, 'value': val})
        
        df = pd.DataFrame(region_records)
        if len(df) > 0:
            outpath = os.path.join(PROC, f'regional_{ind_name}.csv')
            df.to_csv(outpath, index=False)
            all_data[ind_name] = df
            print(f"  {fname} → {ind_name}: {len(df)} records, {df['rayon'].nunique()} regions")
        else:
            print(f"  {fname}: No data extracted")
    
    return all_data


# ── 004 series: Tour operator packages ──
def extract_touroperator():
    print("\n=== Tour Operator Packages (004_1 through 004_13) ===")
    records = []
    for i in range(1, 14):
        fname = f"004_{i}.xls"
        path = os.path.join(RAW, "004_touroperator", fname)
        try:
            wb = xlrd.open_workbook(path)
        except:
            print(f"  WARNING: Cannot open {fname}")
            continue
        ws = wb.sheet_by_index(0)
        
        years = None
        for r in range(min(ws.nrows, 8)):
            years = parse_header_years([ws.cell(r, c).value for c in range(ws.ncols)])
            if years:
                break
        
        if not years:
            print(f"  WARNING: No years found in {fname}")
            continue
        
        title = str(ws.cell(1, 1).value).strip()[:80] if ws.nrows > 1 else fname
        
        for r in range(5, ws.nrows):
            raw_name = str(ws.cell(r, 1).value).strip() if ws.ncols > 1 else ''
            if not raw_name or raw_name in ('о cümlədən:', '', 'o cümlədən:', 'o cümlədən'):
                continue
            if 'Respublikası' in raw_name:
                continue
            name = raw_name.replace('\\n', ' ').replace('\n', ' ').strip()
            
            for c, year in years.items():
                val = parse_az_number(ws.cell(r, c).value)
                if val is not None:
                    records.append({'file': fname, 'title': title, 'region': name, 'year': year, 'value': val})
    
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'tour_operator_packages.csv'), index=False)
    print(f"  Saved {len(df)} records from {df['file'].nunique()} files")
    return df


# ── 002 series: Tourism overview ──
def extract_tourism_overview():
    print("\n=== Tourism Overview (002_1 through 002_4) ===")
    records = []
    for i in range(1, 5):
        fname = f"002_{i}.xls"
        path = os.path.join(RAW, fname)
        try:
            wb = xlrd.open_workbook(path)
        except:
            print(f"  WARNING: Cannot open {fname}")
            continue
        ws = wb.sheet_by_index(0)
        
        years = None
        for r in range(min(ws.nrows, 8)):
            years = parse_header_years([ws.cell(r, c).value for c in range(ws.ncols)])
            if years:
                break
        
        if not years:
            print(f"  WARNING: No years found in {fname}")
            continue
        
        title = str(ws.cell(1, 1).value).strip()[:80] if ws.nrows > 1 else fname
        
        for r in range(5, ws.nrows):
            raw_name = str(ws.cell(r, 1).value).strip() if ws.ncols > 1 else ''
            if not raw_name:
                continue
            name = raw_name.strip()
            
            for c, year in years.items():
                val = parse_az_number(ws.cell(r, c).value)
                if val is not None:
                    records.append({'file': fname, 'title': title, 'indicator': name, 'year': year, 'value': val})
    
    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, 'tourism_overview.csv'), index=False)
    print(f"  Saved {len(df)} records from {df['file'].nunique()} files")
    return df


# ════════════════════════════════════════════════════
# RAYON-ECONOMIC REGION MAPPING
# ════════════════════════════════════════════════════

def build_rayon_lookup():
    """Build mapping from rayon names in GeoJSON to economic regions.
    Extract this from 005 series data structure (organized by economic region)."""
    print("\n=== Building Rayon-Economic Region Lookup ===")
    
    # Economic region structure from 005 series data
    # Based on analyzing the XLS row structure
    region_map = [
        # (rayon_name_az, economic_region_az, economic_region_en)
        # Baku city districts
        ("Binəqədi rayonu", "Bakı", "Baku"),
        ("Xətai rayonu", "Bakı", "Baku"),
        ("Xəzər rayonu", "Bakı", "Baku"),
        ("Qaradağ rayonu", "Bakı", "Baku"),
        ("Nərimanov rayonu", "Bakı", "Baku"),
        ("Nəsimi rayonu", "Bakı", "Baku"),
        ("Nizami rayonu", "Bakı", "Baku"),
        ("Pirallahı rayonu", "Bakı", "Baku"),
        ("Sabunçu rayonu", "Bakı", "Baku"),
        ("Səbail rayonu", "Bakı", "Baku"),
        ("Suraxanı rayonu", "Bakı", "Baku"),
        ("Yasamal rayonu", "Bakı", "Baku"),
        # Nakhchivan
        ("Babək rayonu", "Naxçıvan", "Nakhchivan"),
        ("Culfa rayonu", "Naxçıvan", "Nakhchivan"),
        ("Kəngərli rayonu", "Naxçıvan", "Nakhchivan"),
        ("Ordubad rayonu", "Naxçıvan", "Nakhchivan"),
        ("Sədərək rayonu", "Naxçıvan", "Nakhchivan"),
        ("Şahbuz rayonu", "Naxçıvan", "Nakhchivan"),
        ("Şərur rayonu", "Naxçıvan", "Nakhchivan"),
        # Absheron
        ("Sumqayıt şəhəri", "Abşeron", "Absheron"),
        ("Abşeron rayonu", "Abşeron", "Absheron"),
        ("Xızı rayonu", "Abşeron", "Absheron"),
        # Mountain Shirvan
        ("Ağsu rayonu", "Dağlıq Şirvan", "Mountainous Shirvan"),
        ("İsmayıllı rayonu", "Dağlıq Şirvan", "Mountainous Shirvan"),
        ("Qobustan rayonu", "Dağlıq Şirvan", "Mountainous Shirvan"),
        ("Şamaxı rayonu", "Dağlıq Şirvan", "Mountainous Shirvan"),
        # Ganja-Dashkasan
        ("Gəncə şəhəri", "Gəncə-Daşkəsən", "Ganja-Dashkasan"),
        ("Naftalan şəhəri", "Gəncə-Daşkəsən", "Ganja-Dashkasan"),
        ("Daşkəsən rayonu", "Gəncə-Daşkəsən", "Ganja-Dashkasan"),
        ("Gədəbəy rayonu", "Gəncə-Daşkəsən", "Ganja-Dashkasan"),
        ("Goranboy rayonu", "Gəncə-Daşkəsən", "Ganja-Dashkasan"),
        ("Samux rayonu", "Gəncə-Daşkəsən", "Ganja-Dashkasan"),
        # Karabakh
        ("Xankəndi şəhəri", "Qarabağ", "Karabakh"),
        ("Ağdam rayonu", "Qarabağ", "Karabakh"), 
        ("Tərtər rayonu", "Qarabağ", "Karabakh"),
        ("Xocalı rayonu", "Qarabağ", "Karabakh"),
        ("Xocavənd rayonu", "Qarabağ", "Karabakh"),
        ("Şuşa rayonu", "Qarabağ", "Karabakh"),
        ("Bərdə rayonu", "Qarabağ", "Karabakh"),
        ("Ağcabədi rayonu", "Qarabağ", "Karabakh"),
        # Gazakh-Tovuz
        ("Ağstafa rayonu", "Qazax-Tovuz", "Gazakh-Tovuz"),
        ("Gəy göl rayonu", "Qazax-Tovuz", "Gazakh-Tovuz"),
        ("Qazax rayonu", "Qazax-Tovuz", "Gazakh-Tovuz"),
        ("Tovuz rayonu", "Qazax-Tovuz", "Gazakh-Tovuz"),
        ("Şəmkir rayonu", "Qazax-Tovuz", "Gazakh-Tovuz"),
        # Guba-Khachmaz
        ("Quba rayonu", "Quba-Xaçmaz", "Guba-Khachmaz"),
        ("Qusar rayonu", "Quba-Xaçmaz", "Guba-Khachmaz"),
        ("Xaçmaz rayonu", "Quba-Xaçmaz", "Guba-Khachmaz"),
        ("Siyəzən rayonu", "Quba-Xaçmaz", "Guba-Khachmaz"),
        ("Şabran rayonu", "Quba-Xaçmaz", "Guba-Khachmaz"),
        # Lankaran-Astara
        ("Lənkəran şəhəri", "Lənkəran-Astara", "Lankaran-Astara"),
        ("Astara rayonu", "Lənkəran-Astara", "Lankaran-Astara"),
        ("Cəlilabad rayonu", "Lənkəran-Astara", "Lankaran-Astara"),
        ("Lerik rayonu", "Lənkəran-Astara", "Lankaran-Astara"),
        ("Masallı rayonu", "Lənkəran-Astara", "Lankaran-Astara"),
        ("Yardımlı rayonu", "Lənkəran-Astara", "Lankaran-Astara"),
        # Central Aran
        ("Mingəçevir şəhəri", "Mərkəzi Aran", "Central Aran"),
        ("Yevlax şəhəri", "Mərkəzi Aran", "Central Aran"),
        ("Ağdaş rayonu", "Mərkəzi Aran", "Central Aran"),
        ("Göyçay rayonu", "Mərkəzi Aran", "Central Aran"),
        ("Kürdəmir rayonu", "Mərkəzi Aran", "Central Aran"),
        ("Ucar rayonu", "Mərkəzi Aran", "Central Aran"),
        ("Yevlax rayonu", "Mərkəzi Aran", "Central Aran"),
        ("Zərdab rayonu", "Mərkəzi Aran", "Central Aran"),
        # Mil-Mughan
        ("Beyləqan rayonu", "Mil-Muğan", "Mil-Mughan"),
        ("İmişli rayonu", "Mil-Muğan", "Mil-Mughan"),
        ("Saatlı rayonu", "Mil-Muğan", "Mil-Mughan"),
        ("Sabirabad rayonu", "Mil-Muğan", "Mil-Mughan"),
        # Sheki-Zagatala
        ("Şəki şəhəri", "Şəki-Zaqatala", "Sheki-Zagatala"),
        ("Balakən rayonu", "Şəki-Zaqatala", "Sheki-Zagatala"),
        ("Oğuz rayonu", "Şəki-Zaqatala", "Sheki-Zagatala"),
        ("Qax rayonu", "Şəki-Zaqatala", "Sheki-Zagatala"),
        ("Zaqatala rayonu", "Şəki-Zaqatala", "Sheki-Zagatala"),
        # East Zangazur
        ("Cəbrayıl rayonu", "Şərqi Zəngəzur", "East Zangazur"),
        ("Kəlbəcər rayonu", "Şərqi Zəngəzur", "East Zangazur"),
        ("Qubadlı rayonu", "Şərqi Zəngəzur", "East Zangazur"),
        ("Laçın rayonu", "Şərqi Zəngəzur", "East Zangazur"),
        ("Zəngilan rayonu", "Şərqi Zəngəzur", "East Zangazur"),
    ]
    
    # Turkish/English versions for GeoJSON matching
    tr_map = [
        ("Binəqədi", "Bineqedi", "Baku"),
        ("Xətai", "Khetai", "Baku"),
        ("Xəzər", "Khazar", "Baku"),
        ("Qaradağ", "Garadagh", "Baku"),
        ("Nərimanov", "Nerimanov", "Baku"),
        ("Nəsimi", "Nasimi", "Baku"),
        ("Nizami", "Nizami", "Baku"),
        ("Pirallahı", "Pirallahi", "Baku"),
        ("Sabunçu", "Sabunchu", "Baku"),
        ("Səbail", "Sebail", "Baku"),
        ("Suraxanı", "Surakhani", "Baku"),
        ("Yasamal", "Yasamal", "Baku"),
        ("Babək", "Babek", "Nakhchivan"),
        ("Culfa", "Julfa", "Nakhchivan"),
        ("Kəngərli", "Kengerli", "Nakhchivan"),
        ("Ordubad", "Ordubad", "Nakhchivan"),
        ("Sədərək", "Sedarak", "Nakhchivan"),
        ("Şahbuz", "Shahbuz", "Nakhchivan"),
        ("Şərur", "Sharur", "Nakhchivan"),
        ("Sumqayıt", "Sumgait", "Absheron"),
        ("Abşeron", "Absheron", "Absheron"),
        ("Xızı", "Khizi", "Absheron"),
        ("Ağsu", "Agsu", "Mountainous Shirvan"),
        ("İsmayıllı", "Ismayilli", "Mountainous Shirvan"),
        ("Qobustan", "Gobustan", "Mountainous Shirvan"),
        ("Şamaxı", "Shamakhi", "Mountainous Shirvan"),
        ("Gəncə", "Ganja", "Ganja-Dashkasan"),
        ("Naftalan", "Naftalan", "Ganja-Dashkasan"),
        ("Daşkəsən", "Dashkasan", "Ganja-Dashkasan"),
        ("Gədəbəy", "Gedabey", "Ganja-Dashkasan"),
        ("Goranboy", "Goranboy", "Ganja-Dashkasan"),
        ("Samux", "Samukh", "Ganja-Dashkasan"),
        ("Xankəndi", "Khankendi", "Karabakh"),
        ("Ağdam", "Agdam", "Karabakh"),
        ("Tərtər", "Tartar", "Karabakh"),
        ("Xocalı", "Khojali", "Karabakh"),
        ("Xocavənd", "Khojavend", "Karabakh"),
        ("Şuşa", "Shusha", "Karabakh"),
        ("Bərdə", "Barda", "Karabakh"),
        ("Ağcabədi", "Agjabadi", "Karabakh"),
        ("Ağstafa", "Agstafa", "Gazakh-Tovuz"),
        ("Göygöl", "Goygol", "Gazakh-Tovuz"),
        ("Qazax", "Gazakh", "Gazakh-Tovuz"),
        ("Tovuz", "Tovuz", "Gazakh-Tovuz"),
        ("Şəmkir", "Shamkir", "Gazakh-Tovuz"),
        ("Quba", "Guba", "Guba-Khachmaz"),
        ("Qusar", "Gusar", "Guba-Khachmaz"),
        ("Xaçmaz", "Khachmaz", "Guba-Khachmaz"),
        ("Siyəzən", "Siyazan", "Guba-Khachmaz"),
        ("Şabran", "Shabran", "Guba-Khachmaz"),
        ("Lənkəran", "Lankaran", "Lankaran-Astara"),
        ("Astara", "Astara", "Lankaran-Astara"),
        ("Cəlilabad", "Jalilabad", "Lankaran-Astara"),
        ("Lerik", "Lerik", "Lankaran-Astara"),
        ("Masallı", "Masalli", "Lankaran-Astara"),
        ("Yardımlı", "Yardimli", "Lankaran-Astara"),
        ("Mingəçevir", "Mingachevir", "Central Aran"),
        ("Yevlax", "Yevlakh", "Central Aran"),
        ("Ağdaş", "Agdash", "Central Aran"),
        ("Göyçay", "Goychay", "Central Aran"),
        ("Kürdəmir", "Kurdamir", "Central Aran"),
        ("Ucar", "Ujar", "Central Aran"),
        ("Zərdab", "Zardab", "Central Aran"),
        ("Beyləqan", "Beylagan", "Mil-Mughan"),
        ("İmişli", "Imishli", "Mil-Mughan"),
        ("Saatlı", "Saatli", "Mil-Mughan"),
        ("Sabirabad", "Sabirabad", "Mil-Mughan"),
        ("Şəki", "Shaki", "Sheki-Zagatala"),
        ("Balakən", "Balakan", "Sheki-Zagatala"),
        ("Oğuz", "Oguz", "Sheki-Zagatala"),
        ("Qax", "Gakh", "Sheki-Zagatala"),
        ("Zaqatala", "Zagatala", "Sheki-Zagatala"),
        ("Cəbrayıl", "Jabrayil", "East Zangazur"),
        ("Kəlbəcər", "Kalbajar", "East Zangazur"),
        ("Qubadlı", "Gubadli", "East Zangazur"),
        ("Laçın", "Lachin", "East Zangazur"),
        ("Zəngilan", "Zangilan", "East Zangazur"),
    ]
    
    df = pd.DataFrame(region_map, columns=['rayon_az', 'economic_region_az', 'economic_region_en'])
    df.to_csv(os.path.join(PROC, 'rayon_economic_region.csv'), index=False)
    print(f"  Saved {len(df)} rayon entries")
    return df


# ════════════════════════════════════════════════════
# BUILD REGIONAL PANEL
# ════════════════════════════════════════════════════

def build_regional_panel(regional_data):
    """Merge all regional indicator CSVs into a single panel dataset."""
    print("\n=== Building Regional Panel ===")
    
    # Load geo boundaries to get area
    try:
        gdf = gpd.read_file(os.path.join(GEO, 'azerbaijan_rayon_boundaries.geojson'))
        area_lookup = dict(zip(gdf['adm1_name'], gdf['area_sqkm']))
        print(f"  Loaded {len(area_lookup)} rayon boundaries with areas")
    except:
        area_lookup = {}
        print("  WARNING: Could not load rayon boundaries")
    
    # Load rayon-economic region mapping
    try:
        er_df = pd.read_csv(os.path.join(PROC, 'rayon_economic_region.csv'))
        er_lookup = dict(zip(er_df['rayon_az'], er_df['economic_region_en']))
        print(f"  Loaded {len(er_lookup)} rayon-ER mappings")
    except:
        er_lookup = {}
    
    # Merge all regional indicators
    all_frames = []
    for ind_name, df in regional_data.items():
        if df is None or len(df) == 0:
            continue
        df_pivot = df.pivot_table(index=['rayon', 'year'], values='value', aggfunc='first').reset_index()
        df_pivot = df_pivot.rename(columns={'value': ind_name})
        all_frames.append(df_pivot)
    
    if not all_frames:
        print("  ERROR: No regional data to merge!")
        return None
    
    # Merge all indicators
    panel = all_frames[0]
    for df in all_frames[1:]:
        panel = pd.merge(panel, df, on=['rayon', 'year'], how='outer')
    
    # Add economic region info
    panel['economic_region'] = panel['rayon'].map(er_lookup)
    
    # Add area info - match GeoJSON adm1_name
    # Normalize rayon names for matching
    def norm_name(s):
        s = str(s).lower()
        s = s.replace('şəhəri', '').replace('rayonu', '').replace('şəhər', '')
        s = s.replace('\\n', ' ').replace('\n', ' ').strip()
        return s
    
    adm1_names = {norm_name(k): k for k in area_lookup.keys()}
    
    def find_area(rayon_name):
        n = norm_name(rayon_name)
        # Direct match
        if n in adm1_names:
            return area_lookup[adm1_names[n]]
        # Check without suffixes
        for key, adm1 in adm1_names.items():
            if n in key or key in n:
                return area_lookup[adm1]
        return None
    
    panel['area_sqkm'] = panel['rayon'].apply(find_area)
    panel['year'] = panel['year'].astype(int)
    
    panel.to_csv(os.path.join(PROC, 'regional_panel.csv'), index=False)
    print(f"  Saved panel: {panel.shape[0]} rows, {panel['rayon'].nunique()} regions, {panel['year'].nunique()} years")
    print(f"  Columns: {list(panel.columns)}")
    return panel


# ════════════════════════════════════════════════════
# DERIVED INDICATORS
# ════════════════════════════════════════════════════

def calculate_derived(panel):
    """Calculate all derived indicators from regional panel."""
    print("\n=== Calculating Derived Indicators ===")
    
    if panel is None or len(panel) == 0:
        print("  WARNING: Panel is empty, skipping derived indicators")
        return {}
    
    derived = {}
    
    for year in sorted(panel['year'].unique()):
        sub = panel[panel['year'] == year].copy()
        
        # Hotel Density
        if 'capacity' in sub.columns and 'area_sqkm' in sub.columns:
            sub['hotel_density'] = sub['capacity'] / sub['area_sqkm'].replace(0, np.nan)
        
        # Revenue per Hotel
        if 'revenue' in sub.columns and 'capacity' in sub.columns:
            sub['revenue_per_capacity'] = sub['revenue'] / sub['capacity'].replace(0, np.nan)
        
        # Revenue per Guest
        if 'revenue' in sub.columns and 'guests' in sub.columns:
            sub['revenue_per_guest'] = sub['revenue'] / sub['guests'].replace(0, np.nan)
        
        # Expense per Guest
        if 'expense' in sub.columns and 'guests' in sub.columns:
            sub['expense_per_guest'] = sub['expense'] / sub['guests'].replace(0, np.nan)
        
        # Average Stay
        if 'nights' in sub.columns and 'guests' in sub.columns:
            sub['avg_stay'] = sub['nights'] / sub['guests'].replace(0, np.nan)
        
        # Occupancy proxy
        if 'nights' in sub.columns and 'capacity' in sub.columns:
            sub['occupancy_proxy'] = sub['nights'] / (sub['capacity'] * 365).replace(0, np.nan)
        
        # Employment per capacity
        if 'employees' in sub.columns and 'capacity' in sub.columns:
            sub['emp_per_capacity'] = sub['employees'] / sub['capacity'].replace(0, np.nan)
        
        # Foreign tourist ratio
        if 'guests_foreign' in sub.columns and 'guests' in sub.columns:
            sub['foreign_tourist_ratio'] = sub['guests_foreign'] / sub['guests'].replace(0, np.nan)
        
        # Domestic tourist ratio
        if 'guests_domestic' in sub.columns and 'guests' in sub.columns:
            sub['domestic_tourist_ratio'] = sub['guests_domestic'] / sub['guests'].replace(0, np.nan)
        
        # Revenue - Expense (Profit)
        if 'revenue' in sub.columns and 'expense' in sub.columns:
            sub['profit'] = sub['revenue'] - sub['expense']
        
        # Profit per capacity
        if 'profit' in sub.columns and 'capacity' in sub.columns:
            sub['profit_per_capacity'] = sub['profit'] / sub['capacity'].replace(0, np.nan)
        
        # Foreign nights ratio
        if 'nights_foreign' in sub.columns and 'nights' in sub.columns:
            sub['foreign_night_ratio'] = sub['nights_foreign'] / sub['nights'].replace(0, np.nan)
        
        # Store derived columns
        for col in sub.columns:
            if col not in ('rayon', 'year', 'economic_region', 'area_sqkm') and col not in panel.columns:
                sub[col] = sub[col].fillna(0)
        
        derived[str(year)] = sub.to_dict(orient='records')
    
    # Save
    with open(os.path.join(PROC, 'derived_indicators.json'), 'w') as f:
        json.dump(derived, f, indent=2, default=str)
    print(f"  Saved derived indicators for {len(derived)} years")
    
    # Update panel with derived indicators
    derived_df = pd.concat([pd.DataFrame(v) for k, v in derived.items()])
    
    # Save updated panel
    derived_df.to_csv(os.path.join(PROC, 'regional_panel.csv'), index=False)
    print(f"  Updated panel with derived indicators: {derived_df.shape[1]} columns")
    
    return derived


def main():
    print("=" * 70)
    print("ACCOMMODATION DATA PIPELINE")
    print("=" * 70)
    
    # Extract all data
    extract_hotel_basic()
    extract_hotel_ownership_count()
    extract_ownership_capacity()
    extract_stays_ownership()
    extract_employees()
    extract_revenue_expense()
    extract_rev_exp_ownership()
    extract_foreigner_nights()
    extract_foreigner_stays()
    extract_foreigner_service()
    
    # Regional data
    regional_data = extract_regional_all()
    
    # Tour operator & tourism overview
    extract_touroperator()
    extract_tourism_overview()
    
    # Build lookup
    build_rayon_lookup()
    
    # Build panel
    panel = build_regional_panel(regional_data)
    
    # Calculate derived
    calculate_derived(panel)
    
    print("\n" + "=" * 70)
    print("PIPELINE COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
