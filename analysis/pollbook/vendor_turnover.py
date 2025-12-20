#!/usr/bin/env python3
"""
Analyze poll book turnover patterns over time.

Uses pollbook_transitions.csv to analyze:
- Volume of poll book transitions by year
- Switching patterns between vendors (matrix)
- Adoption vs. departure trends

Reads from: data/processed/pollbook_transitions.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'pollbook'

# Years to analyze
YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# Major vendors to track
VENDORS = ['Paper', 'In-House', 'KNOWiNK', 'ES&S', 'Tenex', 'Other']

# Colors
COLORS = {
    'to_electronic': '#27ae60',   # Green - adoption
    'vendor_change': '#3498db',   # Blue - vendor switch
    'to_paper': '#e74c3c',        # Red - abandonment
}


def categorize_vendor(status):
    """Categorize a poll book status into major vendor categories."""
    if pd.isna(status) or status == '':
        return None
    if status == 'Paper':
        return 'Paper'
    if status == 'In-House':
        return 'In-House'
    if status == 'KNOWiNK':
        return 'KNOWiNK'
    if status == 'ES&S':
        return 'ES&S'
    if status == 'Tenex':
        return 'Tenex'
    return 'Other'


def load_transitions():
    """Load poll book transitions data."""
    filepath = DATA_DIR / 'pollbook_transitions.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Transitions file not found: {filepath}")

    df = pd.read_csv(filepath)

    # Filter out baselines for turnover analysis
    df = df[df['Transition_Type'] != 'baseline'].copy()

    print(f"Loaded {len(df):,} transition records (excluding baselines)")
    return df


def load_time_series():
    """Load time series for jurisdiction totals."""
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'
    df = pd.read_csv(filepath)
    return df


def create_volume_chart(transitions_df, output_path):
    """
    Create chart showing volume of transitions by year and type.

    Args:
        transitions_df: DataFrame of transitions
        output_path: Path to save chart
    """
    # Count transitions by year and type
    volume_data = transitions_df.groupby(['To_Year', 'Transition_Type']).size().unstack(fill_value=0)

    # Ensure all years are represented
    for year in YEARS[1:]:  # Skip 2006 (no transitions to 2006)
        if year not in volume_data.index:
            volume_data.loc[year] = 0
    volume_data = volume_data.sort_index()

    fig, ax = plt.subplots(figsize=(14, 8))

    # Get data for each transition type
    years = volume_data.index.tolist()
    width = 0.25

    transition_types = ['to_electronic', 'vendor_change', 'to_paper']
    labels = ['Paper → Electronic', 'Vendor Change', 'Electronic → Paper']

    for i, (t_type, label) in enumerate(zip(transition_types, labels)):
        if t_type in volume_data.columns:
            values = volume_data[t_type].values
        else:
            values = np.zeros(len(years))

        offset = (i - 1) * width
        bars = ax.bar([y + offset for y in years], values, width,
                      label=label, color=COLORS[t_type], alpha=0.8)

        # Add value labels on bars
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                       f'{int(val)}', ha='center', va='bottom', fontsize=8)

    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Transitions', fontsize=13, fontweight='bold')
    ax.set_title('Poll Book Transitions by Year and Type (2006-2026)',
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(years)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Volume chart saved to {output_path}")


def create_switching_matrix(transitions_df, output_path):
    """
    Create vendor switching matrix heatmap.

    Args:
        transitions_df: DataFrame of transitions
        output_path: Path to save chart
    """
    # Add vendor categories
    transitions_df = transitions_df.copy()
    transitions_df['From_Category'] = transitions_df['From_Poll_Book_Status'].apply(categorize_vendor)
    transitions_df['To_Category'] = transitions_df['To_Poll_Book_Status'].apply(categorize_vendor)

    # Filter to valid categories
    transitions_df = transitions_df[
        transitions_df['From_Category'].notna() &
        transitions_df['To_Category'].notna()
    ]

    # Create pivot table
    matrix = pd.crosstab(
        transitions_df['From_Category'],
        transitions_df['To_Category'],
        margins=True
    )

    # Reorder to match VENDORS list
    vendors_in_data = [v for v in VENDORS if v in matrix.index]
    matrix = matrix.reindex(index=vendors_in_data + ['All'], columns=vendors_in_data + ['All'], fill_value=0)

    # Create heatmap (without totals for visual)
    matrix_display = matrix.drop('All', axis=0).drop('All', axis=1)

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create heatmap
    im = ax.imshow(matrix_display.values, cmap='Blues', aspect='auto')

    # Add labels
    ax.set_xticks(range(len(matrix_display.columns)))
    ax.set_yticks(range(len(matrix_display.index)))
    ax.set_xticklabels(matrix_display.columns, rotation=45, ha='right')
    ax.set_yticklabels(matrix_display.index)

    ax.set_xlabel('To Vendor', fontsize=13, fontweight='bold')
    ax.set_ylabel('From Vendor', fontsize=13, fontweight='bold')
    ax.set_title('Poll Book Vendor Switching Matrix (2006-2026)\n'
                 'Number of Jurisdictions Switching Between Vendors',
                 fontsize=15, fontweight='bold', pad=20)

    # Add text annotations
    for i in range(len(matrix_display.index)):
        for j in range(len(matrix_display.columns)):
            value = matrix_display.iloc[i, j]
            if value > 0:
                color = 'white' if value > matrix_display.values.max() * 0.5 else 'black'
                ax.text(j, i, f'{value:,}', ha='center', va='center',
                       fontsize=10, color=color, fontweight='bold')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Number of Transitions', fontsize=11)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"Switching matrix saved to {output_path}")


def print_summary(transitions_df):
    """Print summary statistics."""
    print("\n" + "=" * 60)
    print("TURNOVER SUMMARY")
    print("=" * 60)

    # By transition type
    print("\nTransitions by type:")
    type_counts = transitions_df['Transition_Type'].value_counts()
    for t_type, count in type_counts.items():
        print(f"  {t_type:20s}: {count:,}")

    # Total electronic adoption
    to_electronic = len(transitions_df[transitions_df['Transition_Type'] == 'to_electronic'])
    to_paper = len(transitions_df[transitions_df['Transition_Type'] == 'to_paper'])
    net_adoption = to_electronic - to_paper

    print(f"\nNet electronic adoption: {net_adoption:+,} jurisdictions")
    print(f"  (Paper → Electronic: {to_electronic:,}, Electronic → Paper: {to_paper:,})")

    # Peak years
    print("\nPeak transition years:")
    year_counts = transitions_df.groupby('To_Year').size().sort_values(ascending=False)
    for year, count in year_counts.head(3).items():
        print(f"  {year}: {count:,} transitions")

    # Most common transitions
    print("\nMost common vendor transitions:")
    transitions_df = transitions_df.copy()
    transitions_df['Transition'] = (
        transitions_df['From_Poll_Book_Status'] + ' -> ' +
        transitions_df['To_Poll_Book_Status']
    )
    transition_counts = transitions_df['Transition'].value_counts()
    for transition, count in transition_counts.head(5).items():
        print(f"  {transition:40s}: {count:,}")


def main():
    print("=" * 80)
    print("POLL BOOK VENDOR TURNOVER ANALYSIS")
    print("=" * 80)
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load transitions data
    print("Loading poll book transitions data...")
    transitions_df = load_transitions()
    print()

    # Create volume chart
    print("Creating transition volume chart...")
    create_volume_chart(transitions_df, OUTPUT_DIR / 'pollbook_transition_volume.png')
    print()

    # Create switching matrix
    print("Creating vendor switching matrix...")
    create_switching_matrix(transitions_df, OUTPUT_DIR / 'pollbook_switching_matrix.png')

    # Print summary
    print_summary(transitions_df)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("Generated files:")
    print(f"  - {OUTPUT_DIR / 'pollbook_transition_volume.png'}")
    print(f"  - {OUTPUT_DIR / 'pollbook_switching_matrix.png'}")
    print()


if __name__ == '__main__':
    main()
