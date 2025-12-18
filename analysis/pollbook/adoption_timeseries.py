#!/usr/bin/env python3
"""
Time series analysis of electronic poll book adoption (2006-2026).

Creates two separate graphs:
1. Number of jurisdictions with electronic poll books over time
2. Registered voters in jurisdictions with electronic poll books over time
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

# Track electronic poll book adoption over time
years = []
electronic_jurisdictions = []
electronic_voters = []
total_jurisdictions = []
total_voters = []

for year in sorted(dfs.keys()):
    df = dfs[year].copy()

    # Clean registered voters column
    df['Registered Voters'] = pd.to_numeric(df['Registered Voters'], errors='coerce')

    # Remove rows with missing data
    df_clean = df[df['Registered Voters'].notna() & df['Poll Book Status'].notna()].copy()

    # Categorize poll book types
    df_clean['Poll Book Type'] = df_clean['Poll Book Status'].apply(
        lambda x: 'Paper' if x == 'Paper' else 'Electronic' if x in ['In-House'] or (x != '' and x != 'Paper') else 'Unknown'
    )

    # Filter to just Paper and Electronic
    df_analysis = df_clean[df_clean['Poll Book Type'].isin(['Paper', 'Electronic'])].copy()

    # Count electronic jurisdictions
    n_electronic = (df_analysis['Poll Book Type'] == 'Electronic').sum()
    n_total = len(df_analysis)

    # Sum voters in electronic jurisdictions
    electronic_voter_count = df_analysis[df_analysis['Poll Book Type'] == 'Electronic']['Registered Voters'].sum()
    total_voter_count = df_analysis['Registered Voters'].sum()

    years.append(year)
    electronic_jurisdictions.append(n_electronic)
    electronic_voters.append(electronic_voter_count)
    total_jurisdictions.append(n_total)
    total_voters.append(total_voter_count)

    print(f"{year}: {n_electronic:4d} jurisdictions ({n_electronic/n_total*100:5.1f}%), {electronic_voter_count:>12,.0f} voters ({electronic_voter_count/total_voter_count*100:5.1f}%)")

# Create first graph: Jurisdictions with electronic poll books
fig1, ax1 = plt.subplots(figsize=(12, 7))

ax1.plot(years, electronic_jurisdictions, marker='o', linewidth=2.5, markersize=8, color='#4169E1')
ax1.fill_between(years, electronic_jurisdictions, alpha=0.3, color='#4169E1')

ax1.set_xlabel('Year', fontsize=14)
ax1.set_ylabel('Number of Jurisdictions', fontsize=14)
ax1.set_title('Growth of Electronic Poll Book Adoption by Jurisdiction Count (2006-2026)',
              fontsize=16, fontweight='bold', pad=20)
ax1.grid(True, alpha=0.3)
ax1.set_xticks(years)

# Add value labels on points
for i, (year, count) in enumerate(zip(years, electronic_jurisdictions)):
    ax1.annotate(f'{count:,}',
                xy=(year, count),
                xytext=(0, 10),
                textcoords='offset points',
                ha='center',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.7))

plt.tight_layout()
plt.savefig('outputs/figures/pollbook/pollbook_adoption_jurisdictions_timeseries.png', dpi=300, bbox_inches='tight')
print("\n✓ Chart 1 saved to outputs/figures/pollbook/pollbook_adoption_jurisdictions_timeseries.png")

# Create second graph: Voters in jurisdictions with electronic poll books
fig2, ax2 = plt.subplots(figsize=(12, 7))

# Convert to millions for easier reading
electronic_voters_millions = [v / 1_000_000 for v in electronic_voters]

ax2.plot(years, electronic_voters_millions, marker='o', linewidth=2.5, markersize=8, color='#228B22')
ax2.fill_between(years, electronic_voters_millions, alpha=0.3, color='#228B22')

ax2.set_xlabel('Year', fontsize=14)
ax2.set_ylabel('Registered Voters (Millions)', fontsize=14)
ax2.set_title('Growth of Electronic Poll Book Coverage by Registered Voters (2006-2026)',
              fontsize=16, fontweight='bold', pad=20)
ax2.grid(True, alpha=0.3)
ax2.set_xticks(years)

# Add value labels on points
for i, (year, count) in enumerate(zip(years, electronic_voters_millions)):
    ax2.annotate(f'{count:.1f}M',
                xy=(year, count),
                xytext=(0, 10),
                textcoords='offset points',
                ha='center',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.7))

plt.tight_layout()
plt.savefig('outputs/figures/pollbook/pollbook_adoption_voters_timeseries.png', dpi=300, bbox_inches='tight')
print("✓ Chart 2 saved to outputs/figures/pollbook/pollbook_adoption_voters_timeseries.png")

# Create third graph: Percentage of voters in jurisdictions with electronic poll books
fig3, ax3 = plt.subplots(figsize=(12, 7))

# Calculate percentages
voter_percentages = [(e / t * 100) for e, t in zip(electronic_voters, total_voters)]

ax3.plot(years, voter_percentages, marker='o', linewidth=2.5, markersize=8, color='#9370DB')
ax3.fill_between(years, voter_percentages, alpha=0.3, color='#9370DB')

ax3.set_xlabel('Year', fontsize=14)
ax3.set_ylabel('Percentage of Registered Voters (%)', fontsize=14)
ax3.set_title('Electronic Poll Book Coverage as Percentage of All Registered Voters (2006-2026)',
              fontsize=16, fontweight='bold', pad=20)
ax3.grid(True, alpha=0.3)
ax3.set_xticks(years)
ax3.set_ylim(0, 100)

# Add value labels on points
for i, (year, pct) in enumerate(zip(years, voter_percentages)):
    ax3.annotate(f'{pct:.1f}%',
                xy=(year, pct),
                xytext=(0, 10),
                textcoords='offset points',
                ha='center',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.7))

plt.tight_layout()
plt.savefig('outputs/figures/pollbook/pollbook_adoption_voters_percentage_timeseries.png', dpi=300, bbox_inches='tight')
print("✓ Chart 3 saved to outputs/figures/pollbook/pollbook_adoption_voters_percentage_timeseries.png")

# Print summary
print("\n" + "="*60)
print("GROWTH SUMMARY")
print("="*60)
print(f"\nJurisdiction count:")
print(f"  2006: {electronic_jurisdictions[0]:>6,} ({electronic_jurisdictions[0]/total_jurisdictions[0]*100:>5.1f}%)")
print(f"  2026: {electronic_jurisdictions[-1]:>6,} ({electronic_jurisdictions[-1]/total_jurisdictions[-1]*100:>5.1f}%)")
print(f"  Growth: {electronic_jurisdictions[-1] - electronic_jurisdictions[0]:>6,} jurisdictions ({(electronic_jurisdictions[-1]/electronic_jurisdictions[0] - 1)*100:>5.1f}% increase)")

print(f"\nRegistered voters:")
print(f"  2006: {electronic_voters[0]:>12,.0f} ({electronic_voters[0]/total_voters[0]*100:>5.1f}%)")
print(f"  2026: {electronic_voters[-1]:>12,.0f} ({electronic_voters[-1]/total_voters[-1]*100:>5.1f}%)")
print(f"  Growth: {electronic_voters[-1] - electronic_voters[0]:>12,.0f} voters ({(electronic_voters[-1]/electronic_voters[0] - 1)*100:>5.1f}% increase)")

print("\n✓ Analysis complete!")
