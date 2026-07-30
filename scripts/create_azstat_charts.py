#!/usr/bin/env python3
"""
Create time-series visualizations from AzStat tourism data.
4 chart groups + dashboard. Turkish labels. DejaVu Sans font.
"""
import os, json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(BASE, "data", "processed")
MODELS = os.path.join(BASE, "models", "azstat")
os.makedirs(MODELS, exist_ok=True)

# Font setup for Turkish characters
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.unicode_minus'] = False

# Color palette
COLORS = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B', '#44BBA4', '#E94F37', '#393E41', '#5D576B', '#7C6A0A']
AZ_BLUE = '#1a5276'
AZ_GREEN = '#1e8449'
AZ_RED = '#922b21'
AZ_GOLD = '#d4ac0d'

# === LOAD DATA ===

def load_border_data():
    df = pd.read_csv(os.path.join(PROC, "azstat_border_totals.csv"))
    df = df[df['year'].between(2015, 2024)]
    return df

def load_border_detailed():
    df = pd.read_csv(os.path.join(PROC, "azstat_border_crossings.csv"))
    df = df[df['year'].between(2015, 2024)]
    return df

def load_transport_data():
    df = pd.read_csv(os.path.join(PROC, "azstat_transport_modes.csv"))
    df = df[df['year'].between(2015, 2024)]
    # Drop 'cəmi' and 'digər' from main display
    return df

def load_purpose_data():
    df = pd.read_csv(os.path.join(PROC, "azstat_purpose_expenditure.csv"))
    df = df[df['year'].between(2015, 2024)]
    return df

def load_country_data():
    df = pd.read_csv(os.path.join(PROC, "azstat_country_origin.csv"))
    df = df[df['year'].between(2015, 2024)]
    return df


# === CHART GROUP 1: BORDER CROSSINGS ===

def chart_border_crossings():
    print("  Creating border crossing charts...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5))

    # --- Line chart: Total border crossings ---
    df = load_border_data()
    df = df.sort_values('year')
    years = df['year'].values
    totals = df['total_border_crossings'].values / 1_000_000  # in millions

    ax1.plot(years, totals, 'o-', color=AZ_BLUE, linewidth=2.5, markersize=8, zorder=3)
    ax1.fill_between(years, totals, alpha=0.15, color=AZ_BLUE)
    ax1.axvline(x=2019, color='orange', linestyle='--', alpha=0.6, label='COVID öncəsi zirvə (2019)')
    ax1.axvline(x=2020, color='red', linestyle='--', alpha=0.4, label='COVID (2020-2021)')

    # Annotate values
    for y, v in zip(years, totals):
        ax1.annotate(f'{v:.1f}M', (y, v), textcoords="offset points", xytext=(0, 12),
                    ha='center', fontsize=8, fontweight='bold', color=AZ_BLUE)

    ax1.set_xlabel('İl', fontsize=12)
    ax1.set_ylabel('Milyon nəfər', fontsize=12)
    ax1.set_title('Sərhəd-Buraxılış Məntəqələrindən Keçən Şəxslərin Sayı\n(2015-2024)', fontsize=13, fontweight='bold')
    ax1.set_xticks(years)
    ax1.set_xticklabels([str(int(y)) for y in years], rotation=45)
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9)

    # --- Bar chart: breakdown by category (most recent year) ---
    df_detailed = load_border_detailed()
    max_yr = int(df_detailed['year'].max())

    categories_ordered = [
        'Daxil olanlar (ümumi)',
        'Daxil olanlar (Azərbaycan vətəndaşları)',
        'Daxil olanlar (əcnəbilər)',
        'Tərk edənlər (ümumi)',
        'Tərk edənlər (Azərbaycan vətəndaşları)',
        'Tərk edənlər (əcnəbilər)',
    ]

    yr_data = df_detailed[df_detailed['year'] == max_yr]
    cat_vals = {}
    for cat in categories_ordered:
        row = yr_data[yr_data['category'] == cat]
        if not row.empty:
            cat_vals[cat] = row.iloc[0]['value']

    # Short labels
    labels = ['Daxil olanlar\n(ümumi)', 'Daxil (Az.\n vətəndaşları)', 'Daxil\n(əcnəbilər)',
              'Tərk edənlər\n(ümumi)', 'Tərk (Az.\n vətəndaşları)', 'Tərk\n(əcnəbilər)']
    vals_mln = [v / 1_000_000 for v in cat_vals.values()]
    bar_colors = [AZ_BLUE, '#3498db', '#85c1e9', AZ_RED, '#e74c3c', '#f1948a']

    bars = ax2.bar(labels, vals_mln, color=bar_colors, edgecolor='white', linewidth=0.5)
    for bar, v in zip(bars, vals_mln):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'{v:.2f}M', ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax2.set_ylabel('Milyon nəfər', fontsize=12)
    ax2.set_title(f'Sərhəd Keçid Kateqoriyaları ({int(max_yr)})', fontsize=13, fontweight='bold')
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(MODELS, 'chart_border_crossings.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    Saved {path}")


# === CHART GROUP 2: TRANSPORT MODES ===

def chart_transport_modes():
    print("  Creating transport mode charts...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5))

    df = load_transport_data()
    df = df[df['transport_type'] != 'cəmi']
    df = df[df['transport_type'] != 'digər']  # 'other' too small/sporadic

    # --- Stacked area chart: Incoming foreigners by transport ---
    incoming = df[df['direction_en'] == 'incoming'].pivot_table(
        index='year', columns='transport_type', values='value', aggfunc='sum'
    ).fillna(0)
    incoming = incoming / 1_000_000  # millions
    incoming = incoming.sort_index()

    transport_labels = {'avtomobil': 'Avtomobil', 'dəmir yolu': 'Dəmir yolu',
                        'hava nəqliyyatı': 'Hava', 'su nəqliyyatı': 'Su'}
    colors = ['#E94F37', '#F18F01', '#2E86AB', '#44BBA4']

    ax1.stackplot(incoming.index, incoming.T.values,
                 labels=[transport_labels.get(c, c) for c in incoming.columns],
                 colors=colors[:len(incoming.columns)], alpha=0.85)
    ax1.set_xlabel('İl', fontsize=12)
    ax1.set_ylabel('Milyon nəfər', fontsize=12)
    ax1.set_title('Azərbaycana Gələn Xarici Ölkə Vətəndaşlarının\nNəqliyyat Növlərinə Görə Bölgüsü', fontsize=13, fontweight='bold')
    ax1.set_xticks(incoming.index)
    ax1.set_xticklabels([str(int(y)) for y in incoming.index], rotation=45)
    ax1.legend(loc='upper left', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # --- Pie chart: Transport mode share (latest year) ---
    incoming_latest = incoming.loc[incoming.index.max()]
    # Filter near-zero
    incoming_latest = incoming_latest[incoming_latest > 0.001]

    wedges, texts, autotexts = ax2.pie(
        incoming_latest.values,
        labels=[f"{transport_labels.get(k, k)}\n({v:.1f}M)" for k, v in incoming_latest.items()],
        colors=colors[:len(incoming_latest)],
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontsize': 9}
    )
    for at in autotexts:
        at.set_fontweight('bold')
    ax2.set_title(f'Nəqliyyat Növü Payı ({int(incoming.index.max())})', fontsize=13, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(MODELS, 'chart_transport_modes.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    Saved {path}")


# === CHART GROUP 3: PURPOSE & EXPENDITURE ===

def chart_purpose_expenditure():
    print("  Creating purpose & expenditure charts...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6.5))

    df = load_purpose_data()

    # --- Line chart: Purpose categories over time (incoming foreigners) ---
    incoming = df[df['visitor_type_en'] == 'incoming_foreigners']
    main_purposes = ['turizm', 'işgüzar', 'müalicə', 'dini', 'qohum ziyarəti', 'digər məqsədlər']
    purpose_labels = {
        'turizm': 'Turizm', 'işgüzar': 'İşgüzar', 'müalicə': 'Müalicə',
        'dini': 'Dini', 'qohum ziyarəti': 'Qohum Ziyarəti', 'digər məqsədlər': 'Digər'
    }
    purpose_colors = [AZ_BLUE, AZ_RED, AZ_GREEN, AZ_GOLD, '#8e44ad', '#7f8c8d']

    for purpose, color in zip(main_purposes, purpose_colors):
        subset = incoming[incoming['purpose'] == purpose].sort_values('year')
        if not subset.empty:
            vals = subset['count'].values / 1_000_000
            years = subset['year'].values
            ax1.plot(years, vals, 'o-', color=color, label=purpose_labels.get(purpose, purpose),
                    linewidth=2, markersize=5)

    ax1.set_xlabel('İl', fontsize=12)
    ax1.set_ylabel('Milyon nəfər', fontsize=12)
    ax1.set_title('Azərbaycana Gələn Əcnəbilərin Səfər Məqsədinə Görə\nBölgüsü (2015-2024)', fontsize=13, fontweight='bold')
    ax1.legend(fontsize=9, loc='upper left')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(sorted(incoming['year'].unique()))
    ax1.set_xticklabels([str(int(y)) for y in sorted(incoming['year'].unique())], rotation=45)

    # --- Bar chart: Purpose breakdown (latest year) ---
    max_yr = int(incoming['year'].max())
    latest = incoming[incoming['year'] == max_yr]
    latest_purposes = latest[latest['purpose'].isin(main_purposes)]

    if not latest_purposes.empty:
        purpose_vals = latest_purposes.set_index('purpose')['count'] / 1_000_000
        # Filter to ensure we have valid data
        purpose_vals = purpose_vals.sort_values(ascending=True)

        labels_short = [purpose_labels.get(k, k) for k in purpose_vals.index]
        bars = ax2.barh(labels_short, purpose_vals.values, color=purpose_colors[:len(purpose_vals)],
                       edgecolor='white', height=0.6)

        for bar, v in zip(bars, purpose_vals.values):
            ax2.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                    f'{v:.2f}M', ha='left', va='center', fontsize=9, fontweight='bold')

    ax2.set_xlabel('Milyon nəfər', fontsize=12)
    ax2.set_title(f'Səfər Məqsədinə Görə Bölgü ({int(max_yr)})', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    path = os.path.join(MODELS, 'chart_purpose_expenditure.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    Saved {path}")


# === CHART GROUP 4: COUNTRY OF ORIGIN ===

def chart_country_origin():
    print("  Creating country of origin charts...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7.5))

    df = load_country_data()

    # --- Bar chart: Top 15 countries (most recent year) ---
    max_yr = int(df['year'].max())
    latest = df[(df['year'] == max_yr) & (df['country'] != 'Cəmi')]
    top15 = latest.nlargest(15, 'visitor_count')

    # Shorten long country names
    name_map = {
        'Rusiya Federasiyası': 'Rusiya',
        'Böyük Britaniya': 'B. Britaniya',
        'Səudiyyə Ərəbistanı': 'S. Ərəbistanı',
        'Cənubi Koreya Respublikası': 'C. Koreya',
        'Birləşmiş Ərəb Əmirlikləri': 'BƏƏ',
        'Efiopiya Federativ Demokratik Respublikası': 'Efiopiya',
    }
    short_names = [name_map.get(c, c) for c in top15['country'].values]

    bars = ax1.barh(range(len(top15)), top15['visitor_count'].values / 1_000,
                   color=plt.cm.Blues(np.linspace(0.4, 0.9, len(top15)))[::-1],
                   edgecolor='white', height=0.6)
    ax1.set_yticks(range(len(top15)))
    ax1.set_yticklabels(short_names, fontsize=9)
    ax1.set_xlabel('Min nəfər', fontsize=12)
    ax1.set_title(f'Azərbaycana Gələn Əcnəbilərin Ölkələr Üzrə Sayı\nİlk 15 Ölkə ({int(max_yr)})', fontsize=13, fontweight='bold')
    ax1.invert_yaxis()
    ax1.grid(True, alpha=0.3, axis='x')

    for bar, v in zip(bars, top15['visitor_count'].values / 1_000):
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{v:.1f}K', ha='left', va='center', fontsize=8, fontweight='bold')

    # --- Heatmap: Top 10 countries over years ---
    # Get top 10 overall countries
    country_totals = df[df['country'] != 'Cəmi'].groupby('country')['visitor_count'].sum()
    top10_countries = country_totals.nlargest(10).index.tolist()

    # Pivot to create year x country matrix
    heat_data = df[df['country'].isin(top10_countries)].pivot_table(
        index='country', columns='year', values='visitor_count', aggfunc='sum'
    ).fillna(0)
    heat_data = heat_data / 1_000  # in thousands
    heat_data = heat_data[sorted(heat_data.columns)]

    im = ax2.imshow(heat_data.values, aspect='auto', cmap='Blues')
    ax2.set_xticks(range(len(heat_data.columns)))
    ax2.set_xticklabels([str(int(y)) for y in heat_data.columns], rotation=45, fontsize=8)
    ax2.set_yticks(range(len(heat_data.index)))
    ax2.set_yticklabels(heat_data.index, fontsize=8)
    ax2.set_title('İlk 10 Ölkə — İllər Üzrə Trend (min nəfər)', fontsize=13, fontweight='bold')

    # Annotate cells
    for i in range(len(heat_data.index)):
        for j in range(len(heat_data.columns)):
            val = heat_data.values[i, j]
            if val > 0:
                text_color = 'white' if val > heat_data.values.max() * 0.5 else 'black'
                ax2.text(j, i, f'{val:.0f}', ha='center', va='center', fontsize=6, color=text_color, fontweight='bold')

    plt.tight_layout()
    path = os.path.join(MODELS, 'chart_country_origin.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    Saved {path}")


# === DASHBOARD: 2x2 grid ===

def chart_dashboard():
    print("  Creating dashboard...")
    fig = plt.figure(figsize=(20, 14))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.25)

    # Re-use individual chart logic but save to subplots
    # Load data
    df_border = load_border_data().sort_values('year')
    df_transport = load_transport_data()
    df_purpose = load_purpose_data()
    df_country = load_country_data()

    # --- Top-left: Border crossings line ---
    ax1 = fig.add_subplot(gs[0, 0])
    years = df_border['year'].values
    totals = df_border['total_border_crossings'].values / 1_000_000
    ax1.plot(years, totals, 'o-', color=AZ_BLUE, linewidth=2.5, markersize=7, zorder=3)
    ax1.fill_between(years, totals, alpha=0.12, color=AZ_BLUE)
    ax1.axvline(x=2019, color='orange', linestyle='--', alpha=0.5)
    for y, v in zip(years, totals):
        ax1.annotate(f'{v:.1f}', (y, v), textcoords="offset points", xytext=(0, 10),
                    ha='center', fontsize=7, fontweight='bold', color=AZ_BLUE)
    ax1.set_title('Sərhəd Keçidləri (milyon)', fontsize=12, fontweight='bold')
    ax1.set_xticks(years)
    ax1.set_xticklabels([str(int(y)) for y in years], rotation=45, fontsize=8)
    ax1.grid(True, alpha=0.3)

    # --- Top-right: Transport modes stacked area ---
    ax2 = fig.add_subplot(gs[0, 1])
    incoming = df_transport[
        (df_transport['direction_en'] == 'incoming') &
        (~df_transport['transport_type'].isin(['cəmi', 'digər']))
    ].pivot_table(index='year', columns='transport_type', values='value', aggfunc='sum').fillna(0) / 1_000_000
    incoming = incoming.sort_index()
    tcolors = ['#E94F37', '#F18F01', '#2E86AB', '#44BBA4']
    tlabels = ['Avtomobil', 'Dəmir yolu', 'Hava', 'Su']
    ax2.stackplot(incoming.index, incoming.T.values, labels=tlabels[:len(incoming.columns)],
                 colors=tcolors[:len(incoming.columns)], alpha=0.85)
    ax2.set_title('Nəqliyyat Növləri (milyon)', fontsize=12, fontweight='bold')
    ax2.set_xticks(incoming.index)
    ax2.set_xticklabels([str(int(y)) for y in incoming.index], rotation=45, fontsize=8)
    ax2.legend(fontsize=7, loc='upper left')
    ax2.grid(True, alpha=0.3)

    # --- Bottom-left: Purpose (incoming, tourism) ---
    ax3 = fig.add_subplot(gs[1, 0])
    incoming_p = df_purpose[df_purpose['visitor_type_en'] == 'incoming_foreigners']
    purposes_plot = ['turizm', 'işgüzar', 'qohum ziyarəti', 'digər məqsədlər']
    pcolors = [AZ_BLUE, AZ_RED, '#8e44ad', '#7f8c8d']
    plabels = ['Turizm', 'İşgüzar', 'Qohum ziy.', 'Digər']
    for purpose, color, label in zip(purposes_plot, pcolors, plabels):
        subset = incoming_p[incoming_p['purpose'] == purpose].sort_values('year')
        if not subset.empty:
            ax3.plot(subset['year'], subset['count'].values / 1_000_000,
                    'o-', color=color, label=label, linewidth=2, markersize=4)
    ax3.set_title('Səfər Məqsədi (milyon)', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(sorted(incoming_p['year'].unique()))
    ax3.set_xticklabels([str(int(y)) for y in sorted(incoming_p['year'].unique())], rotation=45, fontsize=8)

    # --- Bottom-right: Top countries bar ---
    ax4 = fig.add_subplot(gs[1, 1])
    max_yr = int(df_country['year'].max())
    latest_c = df_country[(df_country['year'] == max_yr) & (df_country['country'] != 'Cəmi')]
    top12 = latest_c.nlargest(12, 'visitor_count')
    cname_map = {'Rusiya Federasiyası': 'Rusiya', 'Böyük Britaniya': 'B. Britaniya',
                 'Səudiyyə Ərəbistanı': 'S. Ərəbistanı', 'Birləşmiş Ərəb Əmirlikləri': 'BƏƏ'}
    cnames = [cname_map.get(c, c) for c in top12['country'].values]
    ax4.barh(range(len(top12)), top12['visitor_count'].values / 1_000,
            color=plt.cm.Blues(np.linspace(0.4, 0.9, len(top12)))[::-1], edgecolor='white', height=0.6)
    ax4.set_yticks(range(len(top12)))
    ax4.set_yticklabels(cnames, fontsize=8)
    ax4.set_title(f'İlk 12 Ölkə ({int(max_yr)}, min)', fontsize=12, fontweight='bold')
    ax4.invert_yaxis()
    ax4.grid(True, alpha=0.3, axis='x')

    fig.suptitle('AzStat Turizm İstatistikləri — Zaman Serisi Paneli (2015-2024)',
                fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(MODELS, 'azstat_dashboard.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    Saved {path}")


# === MAIN ===

if __name__ == '__main__':
    print("Creating AzStat time-series charts...")
    chart_border_crossings()
    chart_transport_modes()
    chart_purpose_expenditure()
    chart_country_origin()
    chart_dashboard()
    print("\nAll charts created successfully!")
