#!/usr/bin/env python3
"""
Analyze vendor market share over time based on registered voters.

Generates a stacked area chart showing the market share of Dominion, ES&S,
Hart, and Other vendors from 2006-2026, measured by percentage of registered voters.

Reads from: data/processed/jurisdictions_time_series.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment'

# Major vendors to track separately (use display names)
MAJOR_VENDORS = {
    'Dominion': 'Dominion',
    'ES&S': 'ES&S',
    'Hart InterCivic': 'Hart',
    'Unisyn': 'Unisyn',
    'Clear Ballot': 'Clear Ballot',
}


def categorize_vendor(vendor_name):
    """Map vendor to major category (Dominion, ES&S, Hart, Other)."""
    if pd.isna(vendor_name) or vendor_name == '':
        return 'Other'

    vendor = vendor_name.strip()

    if vendor in MAJOR_VENDORS:
        return MAJOR_VENDORS[vendor]
    else:
        return 'Other'


def load_time_series():
    """
    Load jurisdictions time series data.

    Returns:
        DataFrame with all jurisdiction-year records
    """
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Time series file not found: {filepath}")

    df = pd.read_csv(filepath)
    print(f"✓ Loaded {len(df):,} records from jurisdictions_time_series.csv")

    return df


def calculate_market_share(df):
    """
    Calculate market share by year and vendor category.

    Args:
        df: DataFrame with Year, Primary_Voting_Vendor, Registered_Voters

    Returns:
        dict: {year: {vendor_category: total_voters}}
    """
    # Add vendor category column
    df = df.copy()
    df['Vendor_Category'] = df['Primary_Voting_Vendor'].apply(categorize_vendor)

    # Group by year and vendor category, sum registered voters
    market_share = {}

    for year in sorted(df['Year'].unique()):
        year_df = df[df['Year'] == year]

        # Sum registered voters by vendor category
        vendor_totals = year_df.groupby('Vendor_Category')['Registered_Voters'].sum().to_dict()

        market_share[year] = vendor_totals

    return market_share


def create_market_share_chart(market_share_data):
    """
    Create stacked area chart of vendor market share over time.

    Args:
        market_share_data: dict of {year: {vendor: registered_voters}}
    """
    # Prepare data for stacked area chart
    years = sorted(market_share_data.keys())
    vendors = ['Dominion', 'ES&S', 'Hart', 'Unisyn', 'Clear Ballot', 'Other']

    # Calculate percentages for each vendor per year
    data_by_vendor = {vendor: [] for vendor in vendors}

    for year in years:
        year_data = market_share_data[year]
        total_voters = sum(year_data.values())

        for vendor in vendors:
            voters = year_data.get(vendor, 0)
            percentage = (voters / total_voters * 100) if total_voters > 0 else 0
            data_by_vendor[vendor].append(percentage)

    # Create stacked area chart
    fig, ax = plt.subplots(figsize=(14, 8))

    # Define colors for each vendor
    colors = {
        'Dominion': '#4169E1',    # Royal blue
        'ES&S': '#228B22',        # Forest green
        'Hart': '#9370DB',        # Medium purple
        'Unisyn': '#FF8C00',      # Dark orange
        'Clear Ballot': '#DC143C',  # Crimson
        'Other': '#D3D3D3'        # Light gray
    }

    # Stack the areas
    ax.stackplot(
        years,
        [data_by_vendor[vendor] for vendor in vendors],
        labels=vendors,
        colors=[colors[vendor] for vendor in vendors],
        alpha=0.8
    )

    # Styling
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Market Share (%)', fontsize=13, fontweight='bold')
    ax.set_title('Voting System Vendor Market Share Over Time (2006-2026)\n'
                 'Based on Percentage of Registered Voters',
                 fontsize=15, fontweight='bold', pad=20)

    ax.set_ylim(0, 100)
    ax.set_xlim(min(years), max(years))

    # Add grid
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)

    # Legend
    ax.legend(loc='upper left', fontsize=11, framealpha=0.9)

    # Format x-axis to show all years
    ax.set_xticks(years)
    ax.set_xticklabels([str(y) for y in years], rotation=45, ha='right')

    plt.tight_layout()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / 'vendor_market_share_timeline.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"✓ Chart saved to {output_path}")

    return data_by_vendor


def main():
    """Main processing pipeline."""
    print("=" * 80)
    print("VENDOR MARKET SHARE ANALYSIS")
    print("=" * 80)
    print()

    # Load time series data
    print("Loading jurisdictions time series data...")
    df = load_time_series()
    print()

    # Calculate market share
    print("Calculating market share by year...")
    market_share_data = calculate_market_share(df)
    print(f"✓ Calculated market share for {len(market_share_data)} years")
    print()

    # Print summary statistics
    print("Market Share Summary (First and Last Years):")
    print()

    first_year = min(market_share_data.keys())
    last_year = max(market_share_data.keys())

    for year in [first_year, last_year]:
        print(f"{year}:")
        year_data = market_share_data[year]
        total = sum(year_data.values())

        for vendor in ['Dominion', 'ES&S', 'Hart', 'Unisyn', 'Clear Ballot', 'Other']:
            voters = year_data.get(vendor, 0)
            pct = (voters / total * 100) if total > 0 else 0
            print(f"  {vendor}: {voters:,} voters ({pct:.1f}%)")
        print()

    # Generate stacked area chart
    print("Generating market share timeline chart...")
    data_by_vendor = create_market_share_chart(market_share_data)
    print()

    # Print trend analysis
    print("Market Share Trends:")
    for vendor in ['Dominion', 'ES&S', 'Hart', 'Unisyn', 'Clear Ballot', 'Other']:
        first_pct = data_by_vendor[vendor][0]
        last_pct = data_by_vendor[vendor][-1]
        change = last_pct - first_pct

        direction = "↑" if change > 0 else "↓" if change < 0 else "→"
        print(f"  {vendor}: {first_pct:.1f}% → {last_pct:.1f}% ({direction} {abs(change):.1f} pp)")
    print()

    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Generated file:")
    print(f"  - {OUTPUT_DIR / 'vendor_market_share_timeline.png'}")
    print()


if __name__ == '__main__':
    main()
