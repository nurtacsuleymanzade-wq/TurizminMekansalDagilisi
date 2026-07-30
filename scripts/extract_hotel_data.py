#!/usr/bin/env python3
"""
Extract hotel/accommodation tables using pdfplumber character positions.
This handles thousands-separator spaces properly by using x-coordinates.
"""
import pdfplumber
import csv
import glob
import os
import re
from collections import Counter, defaultdict

SECTIONS = [
    ("5.1",  "Number of hotels and similar establishments (units)",             47, 49),
    ("5.2",  "Once capacity (beds) of hotels (units)",                          49, 51),
    ("5.3",  "Number of rooms in hotels (units)",                               51, 53),
    ("5.4",  "Number of overnights in hotels (nights)",                         53, 56),
    ("5.5",  "Overnights of country citizens in hotels (nights)",               56, 58),
    ("5.6",  "Overnights of foreigners in hotels (nights)",                     58, 60),
    ("5.7",  "Accommodated persons in hotels (persons)",                        60, 62),
    ("5.8",  "Accommodated country citizens in hotels (persons)",               62, 64),
    ("5.9",  "Accommodated foreigners in hotels (persons)",                     64, 67),
    ("5.10", "Income of hotels (thousand manats)",                              67, 69),
    ("5.11", "Expenditures of hotels (thousand manats)",                        69, 71),
    ("5.12", "Number of employees in hotels (persons)",                         71, 74),
]

def parse_num(s):
    if not s or not s.strip():
        return None
    s = s.strip()
    if s in ('-', '...', '…', '', '.'):
        return None
    s = s.replace(' ', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None

def get_line_groups(page):
    """
    Group characters into lines (by y-coordinate), then segment lines into columns.
    Returns list of (line_text, [(col_x_start, col_text), ...]) 
    """
    chars = page.chars
    if not chars:
        return []
    
    # Group chars by line (same y within tolerance)
    lines_dict = defaultdict(list)
    for c in chars:
        # Use rounded y position (top of char) for line grouping
        y_key = round(c['top'], 0)  # 0.5 tolerance
        x_key = c['x0']
        lines_dict[y_key].append((x_key, c['text'], c))
    
    # Sort lines by y, sort chars in each line by x
    sorted_lines = []
    for y_key in sorted(lines_dict.keys()):
        line_chars = sorted(lines_dict[y_key], key=lambda t: t[0])
        line_text = ''.join(c[1] for c in line_chars)
        sorted_lines.append((y_key, line_text, line_chars))
    
    return sorted_lines

def find_year_column_x_ranges(page):
    """
    Find the x-coordinate ranges for each year column (2018-2023).
    Uses the header line that contains '2018 ... 2023'.
    Returns list of (x_start, x_end) for years 2018-2023.
    """
    lines = get_line_groups(page)
    for y, text, chars in lines:
        if '2018' in text and '2019' in text and '2023' in text:
            # Find x positions of each year number
            year_strs = ['2018', '2019', '2020', '2021', '2022', '2023']
            year_positions = []
            for i, (x, ctext, c) in enumerate(chars):
                if ctext in year_strs:
                    year_positions.append((ctext, c['x0'], c['x1']))
            
            if len(year_positions) >= 6:
                # Build column ranges: center between each year label
                ranges = []
                for i in range(6):
                    x0 = year_positions[i][1]
                    x1 = year_positions[i][2]
                    ranges.append((x0, x1))
                
                # Expand ranges to cover the gaps (midpoint between columns)
                expanded = []
                for i in range(6):
                    left = year_positions[i][1] - 8  # some padding
                    right = year_positions[i][2] + 8
                    if i > 0:
                        left = (year_positions[i-1][2] + year_positions[i][1]) / 2
                    if i < 5:
                        right = (year_positions[i][2] + year_positions[i+1][1]) / 2
                    expanded.append((left, right))
                
                return expanded
    
    return None

def extract_data_using_x_coords(page, section_id):
    """
    Extract data rows using character x-coordinates to correctly
    separate region names, year values, and English names.
    """
    lines = get_line_groups(page)
    
    # Find column x-ranges
    col_ranges = find_year_column_x_ranges(page)
    if not col_ranges:
        return []
    
    # Find the data start (after the header line with 2018...2023)
    data_start = 0
    for i, (y, text, chars) in enumerate(lines):
        if '2018' in text and '2019' in text and '2020' in text:
            data_start = i + 1
            break
    
    rows = []
    
    for y, text, chars in lines[data_start:]:
        # Skip header/title lines
        if not text.strip():
            continue
        if text.strip().startswith(('5.', 'VI.', 'ardı', 'continued', 'contiuned',
                                     'Tourism in', 'Azərbaycanda', 'State Statistical',
                                     'İqtisadi rayonlar', 'Economic regions',
                                     'vahid', 'min ', 'gecə', 'persons', 'tour-day',
                                     'thsd')):
            continue
        if re.match(r'^\d+\.\d+\s', text.strip()):
            continue
        
        # Now extract year values based on x-coordinates
        year_values = [None] * 6
        
        # Sort chars by x position
        sorted_chars = sorted(chars, key=lambda t: t[0])
        
        # For each year column, collect overlapping characters
        for yi, (x0, x1) in enumerate(col_ranges):
            val_chars = []
            for x, ctext, c in sorted_chars:
                # Check if char overlaps with this year column
                cx0 = c['x0']
                cx1 = c['x1']
                # Check overlap
                if cx1 > x0 and cx0 < x1:
                    val_chars.append(ctext)
            if val_chars:
                val_text = ''.join(val_chars).strip()
                year_values[yi] = val_text
        
        # Check if we actually got at least some year values
        valid_count = sum(1 for v in year_values if v and v not in ('-', '...', '…', '.'))
        if valid_count == 0:
            continue
        
        # Now extract region name - it's the text to the left of the first year column
        region_chars = []
        first_col_x0 = col_ranges[0][0]
        for x, ctext, c in sorted_chars:
            if c['x1'] < first_col_x0:
                region_chars.append((x, ctext))
        region_chars.sort(key=lambda t: t[0])
        region_name = ''.join(c[1] for c in region_chars).strip()
        
        if not region_name:
            continue
        
        # Remove English translation from region name
        region_name = clean_region_name(region_name)
        
        parsed_vals = [parse_num(v) for v in year_values]
        
        rows.append({
            "region_name": region_name,
            "year_2018": parsed_vals[0],
            "year_2019": parsed_vals[1],
            "year_2020": parsed_vals[2],
            "year_2021": parsed_vals[3],
            "year_2022": parsed_vals[4],
            "year_2023": parsed_vals[5],
            "year_texts": year_values,
        })
    
    return rows


def clean_region_name(name):
    """Remove English translation suffixes from region names."""
    # Common English suffixes that appear after the Azeri name
    eng_patterns = [
        r'\s+Baku city$', r'\s+district$', r'\s+region$', r'\s+economic region$',
        r'\s+Autonomous Republic$', r'\s+Republic$', r'\s+city$',
        r'\s+Nakhchivan', r'\s+Absheron$', r'\s+Khizi$',
        r'\s+Shamakhy$', r'\s+Gobustan$', r'\s+Ismayilly$', r'\s+Aghsu$',
        r'\s+Sumgayit$', r'\s+Ganja$', r'\s+Naftalan$',
        r'\s+Dashkasan$', r'\s+Goranboy$', r'\s+Goygol$', r'\s+Samukh$',
        r'\s+Khankandi$', r'\s+Agdjabadi$', r'\s+Aghdam$', r'\s+Aghdara$',
        r'\s+Barda$', r'\s+Fuzuli$', r'\s+Khojaly$', r'\s+Khojavand$',
        r'\s+Shusha$', r'\s+Terter$',
        r'\s+Agstafa$', r'\s+Gadabey$', r'\s+Gazakh$', r'\s+Shamkir$', r'\s+Tovuz$',
        r'\s+Balakan$', r'\s+Gakh$', r'\s+Gabala$', r'\s+Oguz$', r'\s+Shaki$', r'\s+Zagatala$',
        r'\s+Jabrayil$', r'\s+Kalbajar$', r'\s+Gubadli$', r'\s+Lachin$', r'\s+Zangilan$',
        r'\s+Bilasuvar$', r'\s+Hajigabul$', r'\s+Salyan$', r'\s+Shirvan$',
        r'\s+Khachmaz$', r'\s+Guba$', r'\s+Gusar$', r'\s+Siyazan$', r'\s+Shabran$',
        r'\s+Astara$', r'\s+Jalilabad$', r'\s+Lerik$', r'\s+Lankaran$', r'\s+Masally$', r'\s+Yardimly$',
        r'\s+Mingechevir$', r'\s+Agdash$', r'\s+Goychay$', r'\s+Kurdamir$', r'\s+Ujar$', r'\s+Yevlakh$', r'\s+Zardab$',
        r'\s+Beylagan$', r'\s+Imishli$', r'\s+Saatly$', r'\s+Sabirabad$',
        r'\s+by country', r'\s+total', r'\s+including',
        r'\s+– total$', r'\s+–\s+total$',
    ]
    
    result = name.strip()
    for pat in eng_patterns:
        result = re.sub(pat, '', result)
    
    return result.strip()


def main():
    base_dir = "/tmp/TurizminMekansalDagilisi"
    pdf_glob_path = os.path.join(base_dir, "data/raw/statistics/*2024*.pdf")
    pdf_paths = glob.glob(pdf_glob_path)
    
    if not pdf_paths:
        print("ERROR: No PDF found")
        return
    
    pdf_path = pdf_paths[0]
    output_dir = os.path.join(base_dir, "data/processed")
    os.makedirs(output_dir, exist_ok=True)
    
    all_rows = []
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF: {len(pdf.pages)} pages\n")
        
        for section_id, indicator_name, start_pg, end_pg in SECTIONS:
            print(f"\n{'='*75}")
            print(f"Section {section_id}: {indicator_name}")
            print(f"Pages {start_pg}-{end_pg-1}")
            
            section_rows = 0
            
            for pg_idx in range(start_pg, end_pg):
                if pg_idx >= len(pdf.pages):
                    continue
                
                page = pdf.pages[pg_idx]
                page_num = pg_idx + 1
                
                rows = extract_data_using_x_coords(page, section_id)
                
                for r in rows:
                    all_rows.append({
                        "page_number": page_num,
                        "section_id": section_id,
                        "indicator": indicator_name,
                        "region_name": r["region_name"],
                        "year_2018": r["year_2018"],
                        "year_2019": r["year_2019"],
                        "year_2020": r["year_2020"],
                        "year_2021": r["year_2021"],
                        "year_2022": r["year_2022"],
                        "year_2023": r["year_2023"],
                    })
                    section_rows += 1
                
                if rows:
                    print(f"  Page {page_num}: {len(rows)} rows (e.g. '{rows[0]['region_name'][:45]}')")
                else:
                    print(f"  Page {page_num}: 0 rows")
            
            print(f"  Section total: {section_rows} rows")
    
    # Write CSV
    csv_columns = [
        "page_number", "section_id", "indicator",
        "region_name", 
        "year_2018", "year_2019", "year_2020", "year_2021", "year_2022", "year_2023"
    ]
    
    csv_path = os.path.join(output_dir, "azstat_hotel_stats_2024.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()
        writer.writerows(all_rows)
    
    print(f"\n{'='*75}")
    print(f"RESULTS")
    print(f"{'='*75}")
    print(f"Total rows: {len(all_rows)}")
    print(f"CSV: {csv_path}")
    
    sc = Counter(r['section_id'] for r in all_rows)
    for sid in sorted(sc.keys()):
        print(f"  Section {sid}: {sc[sid]} rows")
    
    # Show sample data
    print("\nSample data (first row of each section):")
    seen_sections = set()
    for r in all_rows:
        if r['section_id'] not in seen_sections:
            seen_sections.add(r['section_id'])
            vals = ' '.join(f"{str(r[f'year_{y}']):>12s}" if r[f'year_{y}'] is not None else '          NaN' for y in range(2018,2024))
            print(f"  [{r['section_id']}] {r['region_name'][:40]:42s} {vals}")

if __name__ == "__main__":
    main()
