#!/usr/bin/env python3
import xlrd

files = [
    ("002_1.xls", "Border crossings"),
    ("002_2.xls", "Transport modes"),
    ("002_3.xls", "Purpose & expenditure"),
    ("002_4.xls", "Country of origin"),
]

import os
base = "data/raw/statistics"

for fname, desc in files:
    fpath = os.path.join(base, fname)
    print(f"\n{'='*60}")
    print(f"FILE: {fname} — {desc}")
    print('='*60)
    wb = xlrd.open_workbook(fpath)
    print(f"Sheets: {wb.sheet_names()}")
    for sname in wb.sheet_names():
        ws = wb.sheet_by_name(sname)
        print(f"\n--- Sheet: '{sname}' ({ws.nrows} rows x {ws.ncols} cols) ---")
        for r in range(min(ws.nrows, 25)):
            row_vals = []
            for c in range(ws.ncols):
                cell = ws.cell(r, c)
                v = cell.value
                if isinstance(v, float) and v == int(v):
                    v = int(v)
                row_vals.append(str(v)[:70])
            print(f"  Row {r}: {row_vals}")
        if ws.nrows > 25:
            print(f"  ... ({ws.nrows - 25} more rows)")
