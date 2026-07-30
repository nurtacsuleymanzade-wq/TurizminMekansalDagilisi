#!/usr/bin/env python3
"""
Extract AzStat tourism data from downloaded .xls files.
Handles Azerbaijani locale number formats (space as thousands sep, comma as decimal).
"""
import os, re, json, csv
import xlrd
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "statistics")
PROC = os.path.join(BASE, "data", "processed")
MODELS = os.path.join(BASE, "models", "azstat")
os.makedirs(PROC, exist_ok=True)
os.makedirs(MODELS, exist_ok=True)


def parse_az_number(s):
    """Parse Azerbaijani number format: '1 234,56' -> 1234.56, also handles '1\\xa0234,56' and '1 234.56'"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if not s or s == '...' or s == '-':
        return None
    # Replace non-breaking spaces, regular spaces, and NBSP
    s = s.replace('\xa0', ' ').replace('\u00a0', ' ')
    # Remove spaces used as thousands separators (but keep decimal)
    # If there's a comma, it's the decimal separator
    if ',' in s:
        # Remove spaces/thousands separators before the comma
        parts = s.split(',')
        integer_part = parts[0].replace(' ', '')
        decimal_part = parts[1] if len(parts) > 1 else '0'
        s = integer_part + '.' + decimal_part
    else:
        # No comma - could still have spaces as thousands sep
        s = s.replace(' ', '')
    try:
        return float(s)
    except ValueError:
        return None


def parse_header_years(row, start_col=1):
    """Parse year headers from a row. Returns {col_index: year} dict."""
    years = {}
    for c in range(start_col, len(row)):
        val = row[c]
        y = None
        if isinstance(val, (int, float)):
            # xlrd stores years as floats (e.g. 2006.0)
            if val == int(val):
                y = int(val)
        elif isinstance(val, str):
            val = val.strip()
            if val and val.isdigit() and len(val) == 4:
                y = int(val)
        if y is not None and 2000 <= y <= 2030:
            years[c] = y
    return years


# ============================================================
# 1. BORDER CROSSINGS (002_1.xls)
# ============================================================
def extract_border_crossings():
    print("\n=== Extracting Border Crossings (002_1.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "002_1.xls"))
    ws = wb.sheet_by_index(0)

    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    if not years:
        print("  WARNING: Could not parse years")
        return None

    print(f"  Years found: {list(years.values())}")

    # Row 4 = total, Row 6 = Azerbaijan citizens, Row 7 = foreigners
    # Row 8 = entries total, Row 10 = entries Azerbaijan citizens, Row 11 = entries foreigners
    # Row 12 = exits total, Row 14 = exits Azerbaijan citizens, Row 15 = exits foreigners
    data_rows = {
        'Ümumi': 4,
        'Azərbaycan vətəndaşları': 6,
        'Əcnəbilər və vətəndaşlığı olmayan şəxslər': 7,
        'Daxil olanlar (ümumi)': 8,
        'Daxil olanlar (Azərbaycan vətəndaşları)': 10,
        'Daxil olanlar (əcnəbilər)': 11,
        'Tərk edənlər (ümumi)': 12,
        'Tərk edənlər (Azərbaycan vətəndaşları)': 14,
        'Tərk edənlər (əcnəbilər)': 15,
    }

    records = []
    for label, row_idx in data_rows.items():
        row_vals = [ws.cell(row_idx, c).value for c in range(ws.ncols)]
        for c, year in years.items():
            val = parse_az_number(row_vals[c])
            if val is not None:
                records.append({
                    'year': year,
                    'category': label,
                    'value_thousands': round(val, 1),
                    'value': round(val * 1000)
                })

    df = pd.DataFrame(records)

    # Also create simplified yearly totals
    yearly_total = {}
    for c, year in years.items():
        val = parse_az_number(ws.cell(4, c).value)
        if val is not None:
            yearly_total[year] = round(val * 1000)

    df_total = pd.DataFrame([
        {'year': y, 'total_border_crossings': v} for y, v in yearly_total.items()
    ])

    df.to_csv(os.path.join(PROC, "azstat_border_crossings.csv"), index=False)
    df_total.to_csv(os.path.join(PROC, "azstat_border_totals.csv"), index=False)
    print(f"  Saved {len(df)} records to azstat_border_crossings.csv")
    print(f"  Yearly totals: {yearly_total}")
    return df, yearly_total


# ============================================================
# 2. TRANSPORT MODES (002_2.xls)
# ============================================================
def extract_transport_modes():
    print("\n=== Extracting Transport Modes (002_2.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "002_2.xls"))
    ws = wb.sheet_by_index(0)

    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    if not years:
        print("  WARNING: Could not parse years")
        return None

    print(f"  Years found: {list(years.values())}")

    # Structure:
    # Row 4: Incoming foreigners total
    # Row 6: automobile (incoming)
    # Row 7: rail (incoming)
    # Row 8: air (incoming)
    # Row 9: sea (incoming)
    # Row 10: other (incoming)
    # Row 11: Outgoing citizens total
    # Row 13: automobile (outgoing)
    # Row 14: rail (outgoing)
    # Row 15: air (outgoing)
    # Row 16: sea (outgoing)
    # Row 17: other (outgoing)

    transport_map = {
        'incoming': {
            'avtomobil': 6,
            'dəmir yolu': 7,
            'hava nəqliyyatı': 8,
            'su nəqliyyatı': 9,
            'digər': 10,
        },
        'outgoing': {
            'avtomobil': 13,
            'dəmir yolu': 14,
            'hava nəqliyyatı': 15,
            'su nəqliyyatı': 16,
            'digər': 17,
        }
    }

    records = []
    for direction, modes in transport_map.items():
        for mode, row_idx in modes.items():
            row_vals = [ws.cell(row_idx, c).value for c in range(ws.ncols)]
            for c, year in years.items():
                val = parse_az_number(row_vals[c])
                if val is not None:
                    records.append({
                        'year': year,
                        'direction': 'gələn' if direction == 'incoming' else 'gedən',
                        'direction_en': direction,
                        'transport_type': mode,
                        'value_thousands': round(val, 1),
                        'value': round(val * 1000)
                    })

    df = pd.DataFrame(records)

    # Also extract totals
    for direction, label, row_idx in [('incoming', 'gələn', 4), ('outgoing', 'gedən', 11)]:
        row_vals = [ws.cell(row_idx, c).value for c in range(ws.ncols)]
        for c, year in years.items():
            val = parse_az_number(row_vals[c])
            if val is not None:
                records.append({
                    'year': year,
                    'direction': label,
                    'direction_en': direction,
                    'transport_type': 'cəmi',
                    'value_thousands': round(val, 1),
                    'value': round(val * 1000)
                })

    df = pd.DataFrame(records)
    df.to_csv(os.path.join(PROC, "azstat_transport_modes.csv"), index=False)
    print(f"  Saved {len(df)} records to azstat_transport_modes.csv")
    return df


# ============================================================
# 3. PURPOSE & EXPENDITURE (002_3.xls)
# ============================================================
def extract_purpose_expenditure():
    print("\n=== Extracting Purpose & Expenditure (002_3.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "002_3.xls"))
    ws = wb.sheet_by_index(0)

    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    if not years:
        print("  WARNING: Could not parse years")
        return None

    print(f"  Years found: {list(years.values())}")

    # Incoming foreigners by purpose
    # Row 4: Total incoming
    # Row 6: Tourism purpose
    # Row 8: Leisure/recreation
    # Row 9: Business
    # Row 10: Medical
    # Row 11: Religious
    # Row 12: Visiting friends/relatives
    # Row 13: Other tourism
    # Row 14: Other purposes

    # Outgoing citizens by purpose
    # Row 15: Total outgoing
    # Row 17: Tourism purpose
    # Row 19: Leisure/recreation
    # Row 20: Business
    # Row 21: Medical
    # Row 22: Religious
    # Row 23: Visiting friends/relatives
    # Row 24: Other tourism
    # Row 25: Other purposes

    # Expenditure rows 26-27
    # Row 26: Expenditure per person (incoming foreigners)
    # Row 27: Expenditure per person (outgoing citizens)

    purpose_records = []

    # Incoming
    incoming_purposes = {
        'cəmi': 4,
        'turizm': 6,
        'istirahət, əyləncə': 8,
        'işgüzar': 9,
        'müalicə': 10,
        'dini': 11,
        'qohum ziyarəti': 12,
        'digər turizm': 13,
        'digər məqsədlər': 14,
    }
    for purpose, row_idx in incoming_purposes.items():
        row_vals = [ws.cell(row_idx, c).value for c in range(ws.ncols)]
        for c, year in years.items():
            val = parse_az_number(row_vals[c])
            if val is not None:
                purpose_records.append({
                    'year': year,
                    'visitor_type': 'Azərbaycana gələn əcnəbilər',
                    'visitor_type_en': 'incoming_foreigners',
                    'purpose': purpose,
                    'count_thousands': round(val, 1),
                    'count': round(val * 1000)
                })

    # Outgoing
    outgoing_purposes = {
        'cəmi': 15,
        'turizm': 17,
        'istirahət, əyləncə': 19,
        'işgüzar': 20,
        'müalicə': 21,
        'dini': 22,
        'qohum ziyarəti': 23,
        'digər turizm': 24,
        'digər məqsədlər': 25,
    }
    for purpose, row_idx in outgoing_purposes.items():
        row_vals = [ws.cell(row_idx, c).value for c in range(ws.ncols)]
        for c, year in years.items():
            val = parse_az_number(row_vals[c])
            if val is not None:
                purpose_records.append({
                    'year': year,
                    'visitor_type': 'Xarici ölkələrə gedən Azərbaycan vətəndaşları',
                    'visitor_type_en': 'outgoing_citizens',
                    'purpose': purpose,
                    'count_thousands': round(val, 1),
                    'count': round(val * 1000)
                })

    # Expenditure data
    try:
        expend_row_in = 26
        expend_row_out = 27
        expend_records = []
        for direction, row_idx, label in [
            ('incoming', expend_row_in, 'Xərclər (gələn əcnəbilər)'),
            ('outgoing', expend_row_out, 'Xərclər (gedən vətəndaşlar)'),
        ]:
            row_vals = [ws.cell(row_idx, c).value for c in range(ws.ncols)]
            print(f"  Expenditure row {row_idx}: {[str(v)[:30] for v in row_vals[:5]]}")
            for c, year in years.items():
                val = parse_az_number(row_vals[c])
                if val is not None:
                    expend_records.append({
                        'year': year,
                        'direction': direction,
                        'label': label,
                        'expenditure_per_person_usd': round(val, 1)
                    })
        df_expend = pd.DataFrame(expend_records)
        df_expend.to_csv(os.path.join(PROC, "azstat_expenditure.csv"), index=False)
        print(f"  Saved {len(df_expend)} expenditure records")
    except Exception as e:
        print(f"  WARNING: Could not extract expenditure: {e}")
        df_expend = None

    df = pd.DataFrame(purpose_records)
    df.to_csv(os.path.join(PROC, "azstat_purpose_expenditure.csv"), index=False)
    print(f"  Saved {len(df)} records to azstat_purpose_expenditure.csv")
    return df, df_expend


# ============================================================
# 4. COUNTRY OF ORIGIN (002_4.xls)
# ============================================================
def extract_country_origin():
    print("\n=== Extracting Country of Origin (002_4.xls) ===")
    wb = xlrd.open_workbook(os.path.join(RAW, "002_4.xls"))
    ws = wb.sheet_by_index(0)

    years = parse_header_years([ws.cell(3, c).value for c in range(ws.ncols)])
    if not years:
        print("  WARNING: Could not parse years")
        return None

    print(f"  Years found: {list(years.values())}")

    # Row 4 is total (Cəmi)
    # Rows 6+ are countries (need to detect blank rows to stop)
    records = []
    for r in range(4, ws.nrows):
        row_vals = [ws.cell(r, c).value for c in range(ws.ncols)]
        country_name = str(row_vals[1]).strip() if row_vals[1] else ''
        if not country_name:
            continue
        # Check if this is a sub-header or blank
        if country_name in ['', 'o cümlədən ölkələr üzrə:', 'o cümlədən:']:
            continue
        if country_name.startswith('o cümlədən'):
            continue

        # Check if it looks like a category header (all caps or short numbers)
        first_data_val = None
        for c in years:
            first_data_val = parse_az_number(row_vals[c])
            if first_data_val is not None:
                break

        if first_data_val is None:
            continue

        # For each year
        for c, year in years.items():
            val = parse_az_number(row_vals[c])
            if val is not None:
                val_int = int(round(val))
                records.append({
                    'year': year,
                    'country': country_name,
                    'visitor_count': val_int
                })

    if not records:
        print("  WARNING: No country data extracted from first sheet, trying second sheet")
        return None

    df = pd.DataFrame(records)

    # Calculate share_percent
    totals_df = df[df['country'] == 'Cəmi'][['year', 'visitor_count']].copy()
    totals_df.columns = ['year', 'total']
    df = df.merge(totals_df, on='year', how='left')
    df['share_percent'] = np.where(
        df['total'] > 0,
        round(df['visitor_count'] / df['total'] * 100, 2),
        0
    )
    df = df.drop(columns=['total'])

    df.to_csv(os.path.join(PROC, "azstat_country_origin.csv"), index=False)
    print(f"  Saved {len(df)} records ({df['country'].nunique()} countries) to azstat_country_origin.csv")

    # Print top countries for latest year
    max_year = df['year'].max()
    top = df[(df['year'] == max_year) & (df['country'] != 'Cəmi')].nlargest(15, 'visitor_count')
    print(f"  Top 15 countries ({max_year}):")
    for _, r in top.iterrows():
        print(f"    {r['country']}: {r['visitor_count']:>8d} ({r['share_percent']:.1f}%)")

    return df


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    bc = extract_border_crossings()
    tm = extract_transport_modes()
    pe = extract_purpose_expenditure()
    co = extract_country_origin()

    print("\n=== Extraction Complete ===")
    print(f"  Border crossings: {'✓' if bc is not None else '✗'}")
    print(f"  Transport modes:  {'✓' if tm is not None else '✗'}")
    print(f"  Purpose & expend: {'✓' if pe is not None else '✗'}")
    print(f"  Country of origin: {'✓' if co is not None else '✗'}")
