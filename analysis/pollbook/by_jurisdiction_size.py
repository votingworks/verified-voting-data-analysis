#!/usr/bin/env python3
"""
Analyze poll book technology adoption by jurisdiction size (2026).

Compare the distribution of jurisdiction sizes (registered voters) between
paper poll book users vs. electronic poll book users.
"""

import sys
from pathlib import Path

# Add project root to path to import utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from utilities import load_year

# Load 2026 data
print("Loading 2026 data...")
df = load_year(2026)

# Clean data - convert registered voters to numeric
df['Registered Voters'] = pd.to_numeric(df['Registered Voters'], errors='coerce')

# Remove rows with missing data
df_clean = df[df['Registered Voters'].notna() & df['Poll Book Status'].notna()].copy()

# Categorize poll book types
df_clean['Poll Book Type'] = df_clean['Poll Book Status'].apply(
    lambda x: 'Paper' if x == 'Paper' else 'Electronic' if x in ['In-House'] or (x != '' and x != 'Paper') else 'Unknown'
)

# Filter to just Paper and Electronic
df_analysis = df_clean[df_clean['Poll Book Type'].isin(['Paper', 'Electronic'])].copy()

print(f"\nAnalyzing {len(df_analysis)} jurisdictions:")
print(f"  Paper poll books: {(df_analysis['Poll Book Type'] == 'Paper').sum()}")
print(f"  Electronic poll books: {(df_analysis['Poll Book Type'] == 'Electronic').sum()}")

# Get data for each group
paper = df_analysis[df_analysis['Poll Book Type'] == 'Paper']['Registered Voters']
electronic = df_analysis[df_analysis['Poll Book Type'] == 'Electronic']['Registered Voters']

# Create histogram
fig, ax = plt.subplots(figsize=(14, 8))

# Create log-spaced bins
bins = np.logspace(np.log10(min(paper.min(), electronic.min())),
                   np.log10(max(paper.max(), electronic.max())),
                   40)

# Plot overlapping histograms
ax.hist(paper, bins=bins, alpha=0.6, label='Paper', color='#808080', edgecolor='black', linewidth=0.5)
ax.hist(electronic, bins=bins, alpha=0.6, label='Electronic', color='#4169E1', edgecolor='black', linewidth=0.5)

ax.set_xscale('log')
ax.set_xlabel('Registered Voters (log scale)', fontsize=14)
ax.set_ylabel('Number of Jurisdictions', fontsize=14)
ax.set_title('Distribution of Jurisdiction Size by Poll Book Type (2026)', fontsize=16, fontweight='bold', pad=20)
ax.legend(fontsize=12, loc='upper right')
ax.grid(True, alpha=0.3, which='both')

plt.tight_layout()
plt.savefig('outputs/figures/pollbook/pollbook_by_jurisdiction_size_2026.png', dpi=300, bbox_inches='tight')
print("\n✓ Chart saved to outputs/figures/pollbook/pollbook_by_jurisdiction_size_2026.png")

# Print summary statistics
print("\n" + "="*60)
print("SUMMARY STATISTICS - 2026")
print("="*60)

for poll_type in ['Paper', 'Electronic']:
    data = df_analysis[df_analysis['Poll Book Type'] == poll_type]['Registered Voters']
    print(f"\n{poll_type} Poll Books ({len(data)} jurisdictions):")
    print(f"  Mean:       {data.mean():>12,.0f} registered voters")
    print(f"  Median:     {data.median():>12,.0f} registered voters")
    print(f"  Min:        {data.min():>12,.0f}")
    print(f"  Max:        {data.max():>12,.0f}")
    print(f"  25th %ile:  {data.quantile(0.25):>12,.0f}")
    print(f"  75th %ile:  {data.quantile(0.75):>12,.0f}")

# Statistical comparison
print("\n" + "="*60)
print("COMPARATIVE ANALYSIS")
print("="*60)

paper_median = paper.median()
elec_median = electronic.median()
print(f"\nMedian jurisdiction size:")
print(f"  Paper:      {paper_median:>12,.0f} voters")
print(f"  Electronic: {elec_median:>12,.0f} voters")
print(f"  Ratio:      {elec_median/paper_median:>12.2f}x (electronic is {elec_median/paper_median:.1f}x larger)")

# What percentage of small vs large jurisdictions use electronic?
small_threshold = df_analysis['Registered Voters'].quantile(0.25)
large_threshold = df_analysis['Registered Voters'].quantile(0.75)

small_juris = df_analysis[df_analysis['Registered Voters'] <= small_threshold]
large_juris = df_analysis[df_analysis['Registered Voters'] >= large_threshold]

print(f"\nElectronic poll book adoption rates:")
print(f"  Smallest 25% of jurisdictions: {(small_juris['Poll Book Type'] == 'Electronic').sum() / len(small_juris) * 100:>5.1f}%")
print(f"  Largest 25% of jurisdictions:  {(large_juris['Poll Book Type'] == 'Electronic').sum() / len(large_juris) * 100:>5.1f}%")
print(f"\nConclusion: Larger jurisdictions are {(large_juris['Poll Book Type'] == 'Electronic').sum() / len(large_juris) / ((small_juris['Poll Book Type'] == 'Electronic').sum() / len(small_juris)):.1f}x more likely to use electronic poll books")

# Calculate voter coverage percentages
print("\n" + "="*60)
print("VOTER COVERAGE ANALYSIS")
print("="*60)

paper_voters = df_analysis[df_analysis['Poll Book Type'] == 'Paper']['Registered Voters'].sum()
electronic_voters = df_analysis[df_analysis['Poll Book Type'] == 'Electronic']['Registered Voters'].sum()
total_voters = paper_voters + electronic_voters

paper_pct = (paper_voters / total_voters) * 100
electronic_pct = (electronic_voters / total_voters) * 100

print(f"\nTotal registered voters covered: {total_voters:>12,.0f}")
print(f"\nVoters in jurisdictions with:")
print(f"  Paper poll books:      {paper_voters:>12,.0f} ({paper_pct:>5.1f}%)")
print(f"  Electronic poll books: {electronic_voters:>12,.0f} ({electronic_pct:>5.1f}%)")
print(f"\nConclusion: {electronic_pct:.1f}% of voters are in jurisdictions using electronic poll books,")
print(f"            even though only {(df_analysis['Poll Book Type'] == 'Electronic').sum() / len(df_analysis) * 100:.1f}% of jurisdictions use them.")

print("\n" + "="*60)
print("\n✓ Analysis complete!")
