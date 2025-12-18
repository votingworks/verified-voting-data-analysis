#!/usr/bin/env python3
"""
Time series analysis of poll book vendor market share (2006-2026).

Creates two stacked area charts showing market share by:
1. Percentage of jurisdictions
2. Percentage of registered voters
"""

import sys
from pathlib import Path

# Add project root to path to import utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import matplotlib.pyplot as plt
from utilities import load_all_years

# Load all years
print("Loading data for all years (2006-2026)...")
dfs = load_all_years()

# Track vendor market share over time
years = []
vendor_data = {
    'Paper': {'jurisdictions': [], 'voters': []},
    'KNOWiNK': {'jurisdictions': [], 'voters': []},
    'In-House': {'jurisdictions': [], 'voters': []},
    'ES&S': {'jurisdictions': [], 'voters': []},
    'Tenex': {'jurisdictions': [], 'voters': []},
    'Other': {'jurisdictions': [], 'voters': []}
}

def categorize_pollbook(status):
    """Categorize poll book status into vendor categories."""
    if pd.isna(status) or status == '' or status == 'Data Unavailable':
        return None
    if status == 'Paper':
        return 'Paper'
    if status == 'In-House':
        return 'In-House'
    if 'KNOWiNK' in status or 'Knowink' in status:
        return 'KNOWiNK'
    if 'ES&S' in status:
        return 'ES&S'
    if 'Tenex' in status:
        return 'Tenex'
    # Everything else is electronic but not one of the main vendors
    return 'Other'

for year in sorted(dfs.keys()):
    df = dfs[year].copy()

    # Clean registered voters column
    df['Registered Voters'] = pd.to_numeric(df['Registered Voters'], errors='coerce')

    # Remove rows with missing data
    df_clean = df[df['Registered Voters'].notna() & df['Poll Book Status'].notna()].copy()

    # Categorize vendors
    df_clean['Vendor'] = df_clean['Poll Book Status'].apply(categorize_pollbook)

    # Remove any None values
    df_clean = df_clean[df_clean['Vendor'].notna()].copy()

    years.append(year)

    total_jurisdictions = len(df_clean)
    total_voters = df_clean['Registered Voters'].sum()

    print(f"\n{year}:")

    # Calculate for each vendor
    for vendor in vendor_data.keys():
        vendor_df = df_clean[df_clean['Vendor'] == vendor]

        n_jurisdictions = len(vendor_df)
        n_voters = vendor_df['Registered Voters'].sum()

        pct_jurisdictions = (n_jurisdictions / total_jurisdictions * 100) if total_jurisdictions > 0 else 0
        pct_voters = (n_voters / total_voters * 100) if total_voters > 0 else 0

        vendor_data[vendor]['jurisdictions'].append(pct_jurisdictions)
        vendor_data[vendor]['voters'].append(pct_voters)

        print(f"  {vendor:10s}: {n_jurisdictions:4d} jurisdictions ({pct_jurisdictions:5.1f}%), {n_voters:>12,.0f} voters ({pct_voters:5.1f}%)")

# Create first chart: Jurisdictions
fig1, ax1 = plt.subplots(figsize=(14, 8))

# Order from bottom to top: Paper, In-House, Other, ES&S, Tenex, KNOWiNK
vendor_order = ['Paper', 'In-House', 'Other', 'ES&S', 'Tenex', 'KNOWiNK']

# Prepare data for stacked area chart
jurisdiction_data = [vendor_data[v]['jurisdictions'] for v in vendor_order]

# Colors: Paper=Medium Grey, In-House=Golden Yellow, Other=Purple, ES&S=Blue, Tenex=Green, KNOWiNK=Coral
colors = ['#808080', '#F4D03F', '#9b59b6', '#3498db', '#27ae60', '#e74c3c']

ax1.stackplot(years, *jurisdiction_data,
              labels=vendor_order,
              colors=colors,
              alpha=0.8)

ax1.set_xlabel('Year', fontsize=14)
ax1.set_ylabel('Percentage of Jurisdictions (%)', fontsize=14)
ax1.set_title('Poll Book Vendor Market Share by Jurisdiction Count (2006-2026)',
              fontsize=16, fontweight='bold', pad=20)
ax1.set_ylim(0, 100)
ax1.set_xticks(years)
ax1.grid(True, alpha=0.3, axis='y')
ax1.legend(loc='upper left', fontsize=11, framealpha=0.9)

plt.tight_layout()
plt.savefig('outputs/figures/pollbook/pollbook_vendor_share_jurisdictions_timeseries.png', dpi=300, bbox_inches='tight')
print("\n✓ Chart 1 saved to outputs/figures/pollbook/pollbook_vendor_share_jurisdictions_timeseries.png")

# Create second chart: Voters
fig2, ax2 = plt.subplots(figsize=(14, 8))

# Prepare data for stacked area chart
voter_data = [vendor_data[v]['voters'] for v in vendor_order]

ax2.stackplot(years, *voter_data,
              labels=vendor_order,
              colors=colors,
              alpha=0.8)

ax2.set_xlabel('Year', fontsize=14)
ax2.set_ylabel('Percentage of Registered Voters (%)', fontsize=14)
ax2.set_title('Poll Book Vendor Market Share by Registered Voters (2006-2026)',
              fontsize=16, fontweight='bold', pad=20)
ax2.set_ylim(0, 100)
ax2.set_xticks(years)
ax2.grid(True, alpha=0.3, axis='y')
ax2.legend(loc='upper left', fontsize=11, framealpha=0.9)

plt.tight_layout()
plt.savefig('outputs/figures/pollbook/pollbook_vendor_share_voters_timeseries.png', dpi=300, bbox_inches='tight')
print("✓ Chart 2 saved to outputs/figures/pollbook/pollbook_vendor_share_voters_timeseries.png")

# Print summary for 2026
print("\n" + "="*60)
print("2026 MARKET SHARE SUMMARY")
print("="*60)

print("\nBy jurisdiction count:")
for vendor in vendor_order:
    pct = vendor_data[vendor]['jurisdictions'][-1]
    print(f"  {vendor:10s}: {pct:5.1f}%")

print("\nBy registered voters:")
for vendor in vendor_order:
    pct = vendor_data[vendor]['voters'][-1]
    print(f"  {vendor:10s}: {pct:5.1f}%")

print("\n✓ Analysis complete!")
