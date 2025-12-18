#!/usr/bin/env python3
"""
Analyze vendor market share over time based on registered voters.

Generates a stacked area chart showing the market share of Dominion, ES&S,
Hart, and Other vendors from 2006-2026, measured by percentage of registered voters.

Reads from: ../data/verifier-condensed/*_verifier-jurisdictions-condensed.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed' / 'jurisdictions'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment'

# Major vendors to track separately
MAJOR_VENDORS = ['Dominion', 'ES&S', 'Hart']

# Years to analyze
YEARS = range(2006, 2028, 2)  # 2006, 2008, ..., 2026


def categorize_vendor(vendor_name):
    """Map vendor to major category (Dominion, ES&S, Hart, Other)."""
    if pd.isna(vendor_name) or vendor_name == '':
        return 'Other'

    vendor = vendor_name.strip()

    if vendor in MAJOR_VENDORS:
        return vendor
    else:
        return 'Other'


def load_year_data(year):
    """
    Load condensed data for a specific year and calculate vendor market share.

    Args:
        year: Year to load (e.g., 2020)

    Returns:
        dict: Vendor -> total registered voters
    """
    filepath = DATA_DIR / f'{year}_verifier-jurisdictions-condensed.csv'

    if not filepath.exists():
        print(f"⚠ Warning: File not found for year {year}")
        return None

    # Read CSV (skip header row)
    df = pd.read_csv(filepath, skiprows=1)

    # Extract relevant columns
    df = df[['Primary Voting Vendor', 'Registered Voters']].copy()

    # Remove rows with missing registered voters
    df = df.dropna(subset=['Registered Voters'])

    # Categorize vendors
    df['Vendor_Category'] = df['Primary Voting Vendor'].apply(categorize_vendor)

    # Sum registered voters by vendor category
    vendor_totals = df.groupby('Vendor_Category')['Registered Voters'].sum().to_dict()

    return vendor_totals


def create_market_share_chart(market_share_data):
    """
    Create stacked area chart of vendor market share over time.

    Args:
        market_share_data: dict of {year: {vendor: registered_voters}}
    """
    # Prepare data for stacked area chart
    years = sorted(market_share_data.keys())
    vendors = ['Dominion', 'ES&S', 'Hart', 'Other']

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

    # Load data for all years
    print("Loading data from condensed CSV files...")
    market_share_data = {}

    for year in YEARS:
        vendor_totals = load_year_data(year)
        if vendor_totals is not None:
            market_share_data[year] = vendor_totals
            total = sum(vendor_totals.values())
            print(f"  {year}: {total:,} total registered voters")

    print(f"\n✓ Loaded {len(market_share_data)} years of data")
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

        for vendor in ['Dominion', 'ES&S', 'Hart', 'Other']:
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
    for vendor in ['Dominion', 'ES&S', 'Hart', 'Other']:
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
    print("  - equipment_analysis/vendor_market_share_timeline.png")
    print()


if __name__ == '__main__':
    main()
