#!/usr/bin/env python3
"""Inspect which hotel sections are on which PDF pages."""
import pdfplumber, glob

pdf_path = glob.glob("data/raw/statistics/*2024*.pdf")[0]
print(f"PDF: {pdf_path}")
with pdfplumber.open(pdf_path) as pdf:
    for i in range(46, 73):
        if i < len(pdf.pages):
            page = pdf.pages[i]
            text = page.extract_text()
            if text:
                lines = text.split('\n')
                key_lines = [l.strip() for l in lines[:5] if l.strip()]
                print(f"PDF p{i+1}: {' | '.join(key_lines[:3])}")
                for line in lines:
                    ls = line.strip()
                    if ls.startswith('5.') and len(ls) > 2:
                        print(f"  SECTION: {ls[:130]}")
                        break
