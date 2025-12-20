#!/usr/bin/env python3
"""
Time series analysis of electronic poll book adoption (2006-2026).

Creates three graphs:
1. Number of jurisdictions with electronic poll books over time
2. Registered voters in jurisdictions with electronic poll books over time
3. Percentage of voters with electronic poll books over time

Reads from: data/processed/jurisdictions_time_series.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'pollbook'


def load_time_series():
    """Load jurisdictions time series data."""
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df):,} records from jurisdictions_time_series.csv")
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
    print("ELECTRONIC POLL BOOK ADOPTION TIMESERIES")
    print("=" * 60)
    print()

    # Load data
    print("Loading jurisdictions time series data...")
    df = load_time_series()
    print()

    # Clean registered voters
    df['Registered_Voters'] = pd.to_numeric(df['Registered_Voters'], errors='coerce')

    # Categorize poll book types
    df['Poll_Book_Type'] = df['Poll_Book_Status'].apply(categorize_pollbook)

    # Remove rows with missing data
    df_clean = df[
        df['Registered_Voters'].notna() &
        df['Poll_Book_Type'].notna()
    ].copy()

    # Aggregate by year
    years = sorted(df_clean['Year'].unique())
    electronic_jurisdictions = []
    electronic_voters = []
    total_jurisdictions = []
    total_voters = []

    print("Processing by year:")
    for year in years:
        year_df = df_clean[df_clean['Year'] == year]

        n_electronic = (year_df['Poll_Book_Type'] == 'Electronic').sum()
        n_total = len(year_df)

        electronic_voter_count = year_df[year_df['Poll_Book_Type'] == 'Electronic']['Registered_Voters'].sum()
        total_voter_count = year_df['Registered_Voters'].sum()

        electronic_jurisdictions.append(n_electronic)
        electronic_voters.append(electronic_voter_count)
        total_jurisdictions.append(n_total)
        total_voters.append(total_voter_count)

        print(f"  {year}: {n_electronic:,} jurisdictions ({n_electronic/n_total*100:.1f}%), "
              f"{electronic_voter_count:,.0f} voters ({electronic_voter_count/total_voter_count*100:.1f}%)")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Chart 1: Jurisdictions with electronic poll books
    fig1, ax1 = plt.subplots(figsize=(12, 7))

    ax1.plot(years, electronic_jurisdictions, marker='o', linewidth=2.5, markersize=8, color='#4169E1')
    ax1.fill_between(years, electronic_jurisdictions, alpha=0.3, color='#4169E1')

    ax1.set_xlabel('Year', fontsize=14)
    ax1.set_ylabel('Number of Jurisdictions', fontsize=14)
    ax1.set_title('Growth of Electronic Poll Book Adoption by Jurisdiction Count (2006-2026)',
                  fontsize=16, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(years)

    # Add value labels
    for year, count in zip(years, electronic_jurisdictions):
        ax1.annotate(f'{count:,}',
                    xy=(year, count),
                    xytext=(0, 10),
                    textcoords='offset points',
                    ha='center',
                    fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.7))

    plt.tight_layout()
    output_path1 = OUTPUT_DIR / 'pollbook_adoption_jurisdictions_timeseries.png'
    plt.savefig(output_path1, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\nChart 1 saved to {output_path1}")

    # Chart 2: Voters in jurisdictions with electronic poll books
    fig2, ax2 = plt.subplots(figsize=(12, 7))

    electronic_voters_millions = [v / 1_000_000 for v in electronic_voters]

    ax2.plot(years, electronic_voters_millions, marker='o', linewidth=2.5, markersize=8, color='#228B22')
    ax2.fill_between(years, electronic_voters_millions, alpha=0.3, color='#228B22')

    ax2.set_xlabel('Year', fontsize=14)
    ax2.set_ylabel('Registered Voters (Millions)', fontsize=14)
    ax2.set_title('Growth of Electronic Poll Book Coverage by Registered Voters (2006-2026)',
                  fontsize=16, fontweight='bold', pad=20)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(years)

    for year, count in zip(years, electronic_voters_millions):
        ax2.annotate(f'{count:.1f}M',
                    xy=(year, count),
                    xytext=(0, 10),
                    textcoords='offset points',
                    ha='center',
                    fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.7))

    plt.tight_layout()
    output_path2 = OUTPUT_DIR / 'pollbook_adoption_voters_timeseries.png'
    plt.savefig(output_path2, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 2 saved to {output_path2}")

    # Chart 3: Percentage of voters with electronic poll books
    fig3, ax3 = plt.subplots(figsize=(12, 7))

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

    for year, pct in zip(years, voter_percentages):
        ax3.annotate(f'{pct:.1f}%',
                    xy=(year, pct),
                    xytext=(0, 10),
                    textcoords='offset points',
                    ha='center',
                    fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.7))

    plt.tight_layout()
    output_path3 = OUTPUT_DIR / 'pollbook_adoption_voters_percentage_timeseries.png'
    plt.savefig(output_path3, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 3 saved to {output_path3}")

    # Print summary
    print("\n" + "=" * 60)
    print("GROWTH SUMMARY")
    print("=" * 60)
    print(f"\nJurisdiction count:")
    print(f"  2006: {electronic_jurisdictions[0]:>6,} ({electronic_jurisdictions[0]/total_jurisdictions[0]*100:>5.1f}%)")
    print(f"  2026: {electronic_jurisdictions[-1]:>6,} ({electronic_jurisdictions[-1]/total_jurisdictions[-1]*100:>5.1f}%)")
    print(f"  Growth: {electronic_jurisdictions[-1] - electronic_jurisdictions[0]:>6,} jurisdictions")

    print(f"\nRegistered voters:")
    print(f"  2006: {electronic_voters[0]:>12,.0f} ({electronic_voters[0]/total_voters[0]*100:>5.1f}%)")
    print(f"  2026: {electronic_voters[-1]:>12,.0f} ({electronic_voters[-1]/total_voters[-1]*100:>5.1f}%)")
    print(f"  Growth: {electronic_voters[-1] - electronic_voters[0]:>12,.0f} voters")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
