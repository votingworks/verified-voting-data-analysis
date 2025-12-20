#!/usr/bin/env python3
"""
Analyze poll book technology adoption by jurisdiction size (2026).

Compare the distribution of jurisdiction sizes (registered voters) between
paper poll book users vs. electronic poll book users.

Reads from: data/processed/jurisdictions_time_series.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'pollbook'


def load_time_series():
    """Load jurisdictions time series data."""
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'
    df = pd.read_csv(filepath)
    return df


def categorize_pollbook(status):
    """Categorize poll book status as Paper or Electronic."""
    if pd.isna(status) or status == '' or status == 'Paper':
        return 'Paper'
    elif status == 'Data Unavailable':
        return None  # Exclude from analysis
    else:
        return 'Electronic'


def main():
    print("=" * 60)
    print("POLL BOOK ADOPTION BY JURISDICTION SIZE (2026)")
    print("=" * 60)
    print()

    # Load data
    print("Loading jurisdictions time series data...")
    df = load_time_series()

    # Filter to 2026
    df = df[df['Year'] == 2026].copy()
    print(f"Loaded {len(df):,} jurisdictions for 2026")

    # Clean registered voters
    df['Registered_Voters'] = pd.to_numeric(df['Registered_Voters'], errors='coerce')

    # Categorize poll book types
    df['Poll_Book_Type'] = df['Poll_Book_Status'].apply(categorize_pollbook)

    # Remove rows with missing data
    df_clean = df[
        df['Registered_Voters'].notna() &
        df['Poll_Book_Type'].notna()
    ].copy()

    # Filter to just Paper and Electronic
    df_analysis = df_clean[df_clean['Poll_Book_Type'].isin(['Paper', 'Electronic'])].copy()

    print(f"\nAnalyzing {len(df_analysis):,} jurisdictions:")
    print(f"  Paper poll books: {(df_analysis['Poll_Book_Type'] == 'Paper').sum():,}")
    print(f"  Electronic poll books: {(df_analysis['Poll_Book_Type'] == 'Electronic').sum():,}")

    # Get data for each group
    paper = df_analysis[df_analysis['Poll_Book_Type'] == 'Paper']['Registered_Voters']
    electronic = df_analysis[df_analysis['Poll_Book_Type'] == 'Electronic']['Registered_Voters']

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
    output_path = OUTPUT_DIR / 'pollbook_by_jurisdiction_size_2026.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\nChart saved to {output_path}")

    # Print summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS - 2026")
    print("=" * 60)

    for poll_type in ['Paper', 'Electronic']:
        data = df_analysis[df_analysis['Poll_Book_Type'] == poll_type]['Registered_Voters']
        print(f"\n{poll_type} Poll Books ({len(data):,} jurisdictions):")
        print(f"  Mean:       {data.mean():>12,.0f} registered voters")
        print(f"  Median:     {data.median():>12,.0f} registered voters")
        print(f"  Min:        {data.min():>12,.0f}")
        print(f"  Max:        {data.max():>12,.0f}")
        print(f"  25th %ile:  {data.quantile(0.25):>12,.0f}")
        print(f"  75th %ile:  {data.quantile(0.75):>12,.0f}")

    # Statistical comparison
    print("\n" + "=" * 60)
    print("COMPARATIVE ANALYSIS")
    print("=" * 60)

    paper_median = paper.median()
    elec_median = electronic.median()
    print(f"\nMedian jurisdiction size:")
    print(f"  Paper:      {paper_median:>12,.0f} voters")
    print(f"  Electronic: {elec_median:>12,.0f} voters")
    print(f"  Ratio:      {elec_median/paper_median:>12.2f}x (electronic is {elec_median/paper_median:.1f}x larger)")

    # What percentage of small vs large jurisdictions use electronic?
    small_threshold = df_analysis['Registered_Voters'].quantile(0.25)
    large_threshold = df_analysis['Registered_Voters'].quantile(0.75)

    small_juris = df_analysis[df_analysis['Registered_Voters'] <= small_threshold]
    large_juris = df_analysis[df_analysis['Registered_Voters'] >= large_threshold]

    small_epb_rate = (small_juris['Poll_Book_Type'] == 'Electronic').sum() / len(small_juris) * 100
    large_epb_rate = (large_juris['Poll_Book_Type'] == 'Electronic').sum() / len(large_juris) * 100

    print(f"\nElectronic poll book adoption rates:")
    print(f"  Smallest 25% of jurisdictions: {small_epb_rate:>5.1f}%")
    print(f"  Largest 25% of jurisdictions:  {large_epb_rate:>5.1f}%")
    if small_epb_rate > 0:
        print(f"\nConclusion: Larger jurisdictions are {large_epb_rate/small_epb_rate:.1f}x more likely to use electronic poll books")

    # Calculate voter coverage percentages
    print("\n" + "=" * 60)
    print("VOTER COVERAGE ANALYSIS")
    print("=" * 60)

    paper_voters = df_analysis[df_analysis['Poll_Book_Type'] == 'Paper']['Registered_Voters'].sum()
    electronic_voters = df_analysis[df_analysis['Poll_Book_Type'] == 'Electronic']['Registered_Voters'].sum()
    total_voters = paper_voters + electronic_voters

    paper_pct = (paper_voters / total_voters) * 100
    electronic_pct = (electronic_voters / total_voters) * 100

    print(f"\nTotal registered voters covered: {total_voters:>12,.0f}")
    print(f"\nVoters in jurisdictions with:")
    print(f"  Paper poll books:      {paper_voters:>12,.0f} ({paper_pct:>5.1f}%)")
    print(f"  Electronic poll books: {electronic_voters:>12,.0f} ({electronic_pct:>5.1f}%)")
    print(f"\nConclusion: {electronic_pct:.1f}% of voters are in jurisdictions using electronic poll books,")
    print(f"            even though only {(df_analysis['Poll_Book_Type'] == 'Electronic').sum() / len(df_analysis) * 100:.1f}% of jurisdictions use them.")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
