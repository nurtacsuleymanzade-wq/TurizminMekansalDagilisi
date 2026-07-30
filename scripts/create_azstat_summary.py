#!/usr/bin/env python3
"""
Create azstat_summary.json with key findings and data aggregations.
"""
import os, json
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed")
MODELS = os.path.join(BASE, "models", "azstat")

# Load all data
border = pd.read_csv(os.path.join(PROC, "azstat_border_totals.csv"))
border = border[border['year'].between(2015, 2024)].sort_values('year')

transport = pd.read_csv(os.path.join(PROC, "azstat_transport_modes.csv"))
transport = transport[transport['year'].between(2015, 2024)]

purpose = pd.read_csv(os.path.join(PROC, "azstat_purpose_expenditure.csv"))
purpose = purpose[purpose['year'].between(2015, 2024)]

country = pd.read_csv(os.path.join(PROC, "azstat_country_origin.csv"))
country = country[country['year'].between(2015, 2024)]

# 1. Yearly totals
yearly_totals = {}
for _, row in border.iterrows():
    y = int(row['year'])
    yearly_totals[str(y)] = int(row['total_border_crossings'])

# 2. Transport breakdown (latest year)
latest_yr = int(border['year'].max())
transport_incoming = transport[
    (transport['year'] == latest_yr) &
    (transport['direction_en'] == 'incoming') &
    (~transport['transport_type'].isin(['cəmi', 'digər']))
]
transport_outgoing = transport[
    (transport['year'] == latest_yr) &
    (transport['direction_en'] == 'outgoing') &
    (~transport['transport_type'].isin(['cəmi', 'digər']))
]

transport_breakdown_latest = {
    'year': latest_yr,
    'incoming': {r['transport_type']: int(r['value']) for _, r in transport_incoming.iterrows()},
    'outgoing': {r['transport_type']: int(r['value']) for _, r in transport_outgoing.iterrows()},
}

# Calculate shares
total_in = sum(transport_breakdown_latest['incoming'].values())
total_out = sum(transport_breakdown_latest['outgoing'].values())
transport_breakdown_latest['incoming_share_pct'] = {
    k: round(v / total_in * 100, 1) for k, v in transport_breakdown_latest['incoming'].items()
} if total_in > 0 else {}
transport_breakdown_latest['outgoing_share_pct'] = {
    k: round(v / total_out * 100, 1) for k, v in transport_breakdown_latest['outgoing'].items()
} if total_out > 0 else {}

# 3. Top countries (latest year)
latest_countries = country[(country['year'] == latest_yr) & (country['country'] != 'Cəmi')]
top_countries = []
for _, row in latest_countries.nlargest(20, 'visitor_count').iterrows():
    top_countries.append({
        'country': row['country'],
        'visitor_count': int(row['visitor_count']),
        'share_pct': round(row['share_percent'], 1)
    })

# 4. Purpose breakdown (latest year)
incoming_purpose = purpose[
    (purpose['year'] == latest_yr) &
    (purpose['visitor_type_en'] == 'incoming_foreigners') &
    (~purpose['purpose'].isin(['cəmi']))
]
purpose_breakdown = {}
for _, row in incoming_purpose.iterrows():
    if row['purpose'] in ['turizm', 'işgüzar', 'müalicə', 'dini', 'qohum ziyarəti', 'digər məqsədlər', 'digər turizm']:
        purpose_breakdown[row['purpose']] = int(row['count'])

# Calculate tourism sub-shares
tourism_total = sum(v for k, v in purpose_breakdown.items())
purpose_shares = {k: round(v / tourism_total * 100, 1) for k, v in purpose_breakdown.items()} if tourism_total > 0 else {}

# 5. Expenditure (from our extracted data)
expenditure = pd.read_csv(os.path.join(PROC, "azstat_expenditure.csv")) if os.path.exists(os.path.join(PROC, "azstat_expenditure.csv")) else None
expenditure_breakdown = {}
if expenditure is not None and not expenditure.empty:
    for _, row in expenditure.iterrows():
        key = f"{int(row['year'])}_{row['direction']}"
        expenditure_breakdown[str(int(row['year']))] = expenditure_breakdown.get(str(int(row['year'])), {})
        expenditure_breakdown[str(int(row['year']))][row['direction']] = row['expenditure_per_person_usd']

# 6. Key trends in Turkish
total_2019 = yearly_totals.get('2019', 0)
total_2020 = yearly_totals.get('2020', 0)
total_2024 = yearly_totals.get('2024', 0)

drop_2020_pct = round((total_2019 - total_2020) / total_2019 * 100, 1) if total_2019 > 0 else 0
recovery_pct = round((total_2024 - total_2020) / total_2020 * 100, 1) if total_2020 > 0 else 0
vs_2019_pct = round(total_2024 / total_2019 * 100, 1) if total_2019 > 0 else 0

# Russia share
russia_2024 = None
for c in top_countries:
    if 'Rusiya' in c['country']:
        russia_2024 = c['share_pct']
        break

# Air share
air_share = transport_breakdown_latest['incoming_share_pct'].get('hava nəqliyyatı', 0)

key_trends = [
    f"COVID-19 pandemiyası səbəbindən 2020-ci ildə sərhəd keçidləri {drop_2020_pct}% azalaraq {total_2020:,} nəfərə düşüb (2019: {total_2019:,} nəfər).",
    f"2024-cü ildə toparlanma davam edir: {total_2024:,} nəfər keçid qeydə alınıb (2019 səviyyəsinin {vs_2019_pct}%).",
    f"Hava nəqliyyatı gələn əcnəbilər arasında {air_share}% payla əsas nəqliyyat növüdür. Rusiya Federasiyası ({russia_2024}% pay) ən böyük mənbə ölkə olaraq qalır."
]

summary = {
    "meta": {
        "source": "Azərbaycan Respublikasının Dövlət Statistika Komitəsi (AzStat)",
        "url": "https://www.stat.gov.az/source/tourism/",
        "data_files": [
            "002_1.xls - Sərhəd-buraxılış məntəqələrindən keçən şəxslərin sayı",
            "002_2.xls - Nəqliyyat növlərindən istifadə üzrə sayı",
            "002_3.xls - Səfərlərin məqsədi üzrə bölgüsü və xərclər",
            "002_4.xls - Ölkələr üzrə gələn əcnəbilərin sayı"
        ],
        "data_period": "2015-2024",
        "data_type": "real",
        "notes": "Məlumatlar birbaşa AzStat rəsmi XLS fayllarından çıxarılıb. Qiymətlər 'min nəfər' ilə verilmişdir, milyonlara çevrilmişdir."
    },
    "yearly_totals": yearly_totals,
    "transport_breakdown_latest": transport_breakdown_latest,
    "top_countries": top_countries,
    "purpose_breakdown": purpose_breakdown,
    "purpose_shares": purpose_shares,
    "expenditure_breakdown": expenditure_breakdown,
    "key_trends": key_trends,
    "summary_stats": {
        "peak_year": "2019",
        "peak_value": total_2019,
        "covid_drop_pct": drop_2020_pct,
        "recovery_2024_vs_2019_pct": vs_2019_pct,
        "recovery_2024_vs_2020_pct": recovery_pct,
        "latest_year": latest_yr,
        "latest_value": total_2024,
        "top_source_country": top_countries[0]['country'] if top_countries else None,
        "top_source_country_share": top_countries[0]['share_pct'] if top_countries else None,
        "dominant_transport": "hava nəqliyyatı",
        "dominant_transport_share": air_share
    }
}

# Convert numpy types to Python native
def convert(obj):
    if isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    return obj

summary = convert(summary)

path = os.path.join(PROC, "azstat_summary.json")
with open(path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"Saved {path}")
print(f"Key trends: {len(key_trends)} items")
print(f"Yearly totals: {len(yearly_totals)} years")
print(f"Top countries: {len(top_countries)}")
