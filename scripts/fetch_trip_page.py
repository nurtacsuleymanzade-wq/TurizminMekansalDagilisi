#!/usr/bin/env python3
"""Fetch trip pages from azerbaijan.travel and extract structured data."""
import requests
import re
import json
import sys

def fetch_page(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    print(f'Status: {resp.status_code}, Size: {len(resp.text)} chars, URL: {resp.url}', file=sys.stderr)
    return resp.text

def analyze_html(html, label):
    print(f'\n=== {label} ===')
    # Meta description
    m = re.search(r'<meta name="description" content="([^"]+)"', html)
    if m: print(f'DESC: {m.group(1)[:200]}')
    
    # Title
    m = re.search(r'<title>([^<]+)</title>', html)
    if m: print(f'TITLE: {m.group(1)[:200]}')
    
    # JSON-LD
    jsonlds = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    for j in jsonlds:
        try:
            data = json.loads(j)
            print(f'JSON-LD: {json.dumps(data, indent=2)[:1000]}')
        except:
            print(f'JSON-LD (raw): {j[:300]}')
    
    # Check for inline data
    for pattern in [r'window\.__NUXT__\s*=', r'window\.__INITIAL_STATE__\s*=', r'"places"', r'"destinations"', r'"coordinates"']:
        if re.search(pattern, html, re.IGNORECASE):
            print(f'FOUND: {pattern}')
    
    # Find all script src
    scripts = re.findall(r'<script[^>]*src="([^"]*)"', html)
    for s in scripts:
        if any(k in s.lower() for k in ['api', 'data', 'config']):
            print(f'SCRIPT: {s}')
    
    # Check body text content
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
    if body_match:
        body_text = re.sub(r'<[^>]+>', ' ', body_match.group(1))
        body_text = re.sub(r'\s+', ' ', body_text).strip()
        print(f'BODY TEXT (first 500): {body_text[:500]}')

if __name__ == '__main__':
    urls = [
        'https://azerbaijan.travel/trip-to-guba',
        'https://azerbaijan.travel/trip-to-sheki',
    ]
    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    
    for url in urls:
        html = fetch_page(url)
        analyze_html(html, url)
        # Save for inspection
        safe_name = url.replace('https://', '').replace('/', '_')
        with open(f'/tmp/TurizminMekansalDagilisi/data/raw/{safe_name}.html', 'w') as f:
            f.write(html)
