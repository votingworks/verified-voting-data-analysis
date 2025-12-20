#!/usr/bin/env python3
"""
Time series analysis of voting equipment adoption (2006-2026).

Shows the portion of jurisdictions/voters using any voting equipment
(i.e., not hand count).

Creates four graphs:
1. Number of jurisdictions with voting equipment over time
2. Registered voters in jurisdictions with voting equipment over time
3. Percentage of voters with voting equipment over time
4. Hand count transitions (diverging bar chart showing adoption vs abandonment)

Reads from:
- data/processed/jurisdictions_time_series.csv
- data/processed/jurisdiction_transitions.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment'

# Years to analyze
YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]


def load_time_series():
    """Load jurisdictions time series data."""
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df):,} records from jurisdictions_time_series.csv")
    return df


def has_equipment(voting_class):
    """Check if jurisdiction uses voting equipment (not hand count)."""
    if pd.isna(voting_class) or voting_class == '':
        return None  # Exclude from analysis
    return voting_class != 'Hand Count'


def load_transitions():
    """Load jurisdiction transitions data."""
    filepath = DATA_DIR / 'jurisdiction_transitions.csv'
    df = pd.read_csv(filepath)
    print(f"Loaded {len(df):,} records from jurisdiction_transitions.csv")
    return df


def create_hand_count_transitions_chart(output_path):
    """
    Create diverging bar chart showing hand count transitions by year.

    Shows from_hand_count events (adoption) above x-axis and
    to_hand_count events (abandonment) below x-axis.
    """
    print("\nCreating hand count transitions chart...")

    # Load transitions data
    transitions_df = load_transitions()

    # Filter to hand count transitions only
    hand_count_df = transitions_df[
        transitions_df['Transition_Type'].isin(['from_hand_count', 'to_hand_count'])
    ].copy()

    # Group by year and transition type
    counts = hand_count_df.groupby(['To_Year', 'Transition_Type']).size().unstack(fill_value=0)

    # Ensure all years are represented (skip 2006 - no transitions to 2006)
    for year in YEARS[1:]:
        if year not in counts.index:
            counts.loc[year] = 0
    counts = counts.sort_index()

    # Get counts for each type
    years = counts.index.tolist()
    from_hand_count = counts.get('from_hand_count', pd.Series(0, index=years)).values
    to_hand_count = counts.get('to_hand_count', pd.Series(0, index=years)).values

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))

    # Bar width
    width = 1.5

    # Plot from_hand_count (positive, above x-axis) - green for adoption
    ax.bar(years, from_hand_count, width, label='Adopted Equipment (from hand count)',
           color='#27ae60', alpha=0.85)

    # Plot to_hand_count (negative, below x-axis) - red for abandonment
    ax.bar(years, -to_hand_count, width, label='Returned to Hand Count',
           color='#e74c3c', alpha=0.85)

    # Add value labels on bars
    for i, (year, from_val, to_val) in enumerate(zip(years, from_hand_count, to_hand_count)):
        if from_val > 0:
            ax.text(year, from_val + 5, str(from_val), ha='center', va='bottom',
                    fontsize=10, fontweight='bold')
        if to_val > 0:
            ax.text(year, -to_val - 5, str(to_val), ha='center', va='top',
                    fontsize=10, fontweight='bold')

    # Add horizontal line at y=0
    ax.axhline(y=0, color='black', linewidth=1)

    # Formatting
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Jurisdictions', fontsize=13, fontweight='bold')
    ax.set_title('Hand Count Transitions by Year (2008-2026)\n'
                 'Jurisdictions Adopting Equipment (↑) vs Returning to Hand Count (↓)',
                 fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(years)
    ax.legend(fontsize=11, loc='lower right')
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    # Set y-axis to be symmetric around 0
    max_val = max(from_hand_count.max(), to_hand_count.max())
    ax.set_ylim(-max_val * 1.15, max_val * 1.15)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    # Print summary
    total_from = from_hand_count.sum()
    total_to = to_hand_count.sum()
    net = total_from - total_to
    print(f"  Total adoptions (from hand count): {total_from:,}")
    print(f"  Total abandonments (to hand count): {total_to:,}")
    print(f"  Net equipment adoption: {net:+,}")
    print(f"Chart saved to {output_path}")


def main():
    print("=" * 60)
    print("VOTING EQUIPMENT ADOPTION TIMESERIES")
    print("=" * 60)
    print()

    # Load data
    print("Loading jurisdictions time series data...")
    df = load_time_series()
    print()

    # Clean registered voters
    df['Registered_Voters'] = pd.to_numeric(df['Registered_Voters'], errors='coerce')

    # Categorize by equipment usage
    df['Has_Equipment'] = df['Voting_Class'].apply(has_equipment)

    # Remove rows with missing data
    df_clean = df[
        df['Registered_Voters'].notna() &
        df['Has_Equipment'].notna()
    ].copy()

    # Aggregate by year
    years = sorted(df_clean['Year'].unique())
    equipment_jurisdictions = []
    equipment_voters = []
    total_jurisdictions = []
    total_voters = []

    print("Processing by year:")
    for year in years:
        year_df = df_clean[df_clean['Year'] == year]

        n_equipment = year_df['Has_Equipment'].sum()
        n_total = len(year_df)

        equipment_voter_count = year_df[year_df['Has_Equipment']]['Registered_Voters'].sum()
        total_voter_count = year_df['Registered_Voters'].sum()

        equipment_jurisdictions.append(n_equipment)
        equipment_voters.append(equipment_voter_count)
        total_jurisdictions.append(n_total)
        total_voters.append(total_voter_count)

        print(f"  {year}: {n_equipment:,} jurisdictions ({n_equipment/n_total*100:.1f}%), "
              f"{equipment_voter_count:,.0f} voters ({equipment_voter_count/total_voter_count*100:.1f}%)")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Chart 1: Jurisdictions with voting equipment
    fig1, ax1 = plt.subplots(figsize=(12, 7))

    ax1.plot(years, equipment_jurisdictions, marker='o', linewidth=2.5, markersize=8, color='#4169E1')
    ax1.fill_between(years, equipment_jurisdictions, alpha=0.3, color='#4169E1')

    ax1.set_xlabel('Year', fontsize=14)
    ax1.set_ylabel('Number of Jurisdictions', fontsize=14)
    ax1.set_title('Jurisdictions Using Voting Equipment (Not Hand Count) (2006-2026)',
                  fontsize=16, fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(years)

    plt.tight_layout()
    output_path1 = OUTPUT_DIR / 'equipment_adoption_jurisdictions_timeseries.png'
    plt.savefig(output_path1, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\nChart 1 saved to {output_path1}")

    # Chart 2: Voters in jurisdictions with voting equipment
    fig2, ax2 = plt.subplots(figsize=(12, 7))

    equipment_voters_millions = [v / 1_000_000 for v in equipment_voters]

    ax2.plot(years, equipment_voters_millions, marker='o', linewidth=2.5, markersize=8, color='#228B22')
    ax2.fill_between(years, equipment_voters_millions, alpha=0.3, color='#228B22')

    ax2.set_xlabel('Year', fontsize=14)
    ax2.set_ylabel('Registered Voters (Millions)', fontsize=14)
    ax2.set_title('Registered Voters in Jurisdictions Using Voting Equipment (2006-2026)',
                  fontsize=16, fontweight='bold', pad=20)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(years)

    plt.tight_layout()
    output_path2 = OUTPUT_DIR / 'equipment_adoption_voters_timeseries.png'
    plt.savefig(output_path2, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 2 saved to {output_path2}")

    # Chart 3: Percentage of voters with voting equipment
    fig3, ax3 = plt.subplots(figsize=(12, 7))

    voter_percentages = [(e / t * 100) for e, t in zip(equipment_voters, total_voters)]

    ax3.plot(years, voter_percentages, marker='o', linewidth=2.5, markersize=8, color='#9370DB')
    ax3.fill_between(years, voter_percentages, alpha=0.3, color='#9370DB')

    ax3.set_xlabel('Year', fontsize=14)
    ax3.set_ylabel('Percentage of Registered Voters (%)', fontsize=14)
    ax3.set_title('Voting Equipment Coverage as Percentage of All Registered Voters (2006-2026)',
                  fontsize=16, fontweight='bold', pad=20)
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(years)
    ax3.set_ylim(0, 105)

    plt.tight_layout()
    output_path3 = OUTPUT_DIR / 'equipment_adoption_voters_percentage_timeseries.png'
    plt.savefig(output_path3, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Chart 3 saved to {output_path3}")

    # Chart 4: Hand count transitions (diverging bar chart)
    output_path4 = OUTPUT_DIR / 'hand_count_transitions.png'
    create_hand_count_transitions_chart(output_path4)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nJurisdiction count:")
    print(f"  2006: {equipment_jurisdictions[0]:>6,} / {total_jurisdictions[0]:>6,} ({equipment_jurisdictions[0]/total_jurisdictions[0]*100:>5.1f}%)")
    print(f"  2026: {equipment_jurisdictions[-1]:>6,} / {total_jurisdictions[-1]:>6,} ({equipment_jurisdictions[-1]/total_jurisdictions[-1]*100:>5.1f}%)")

    print(f"\nRegistered voters:")
    print(f"  2006: {equipment_voters[0]:>12,.0f} / {total_voters[0]:>12,.0f} ({equipment_voters[0]/total_voters[0]*100:>5.1f}%)")
    print(f"  2026: {equipment_voters[-1]:>12,.0f} / {total_voters[-1]:>12,.0f} ({equipment_voters[-1]/total_voters[-1]*100:>5.1f}%)")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    main()
