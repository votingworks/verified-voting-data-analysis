#!/usr/bin/env python3
"""
Analyze equipment upgrade recency by state.

For each state, shows:
1. Bar chart of when jurisdictions last upgraded (vendor or system change)
2. Summary statistics (median, mean, std dev of upgrade years)

Outputs:
- Per-state bar charts: outputs/figures/equipment/state_recency/{state}_recency.png
- Summary report: outputs/reports/state_equipment_recency.txt

Reads from: data/processed/jurisdiction_transitions.csv
"""

import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
EQUIPMENT_FIGURES_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'equipment'
FIGURES_DIR = EQUIPMENT_FIGURES_DIR / 'state_recency'
REPORTS_DIR = PROJECT_ROOT / 'outputs' / 'reports'

# Years to show on charts (includes "pre-2006" bucket for older equipment)
CHART_YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]
CHART_LABELS = ['Pre-2006', '2006', '2008', '2010', '2012', '2014', '2016', '2018', '2020', '2022', '2024', '2026']

# Transition types that count as "upgrades"
UPGRADE_TYPES = {'vendor', 'system'}

# State abbreviations mapping
STATE_ABBREVS = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
    'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
    'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
    'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
    'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC',
}


def load_transitions():
    """Load jurisdiction transitions data."""
    filepath = DATA_DIR / 'jurisdiction_transitions.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Transitions file not found: {filepath}")

    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['To_Year'] = int(row['To_Year'])
            records.append(row)

    return records


def get_most_recent_upgrades(records):
    """
    Find the most recent upgrade year for each jurisdiction.

    For jurisdictions that have upgraded, returns the year of most recent upgrade.
    For jurisdictions that never upgraded, returns their baseline year (original
    equipment installation date).

    Args:
        records: List of transition records

    Returns:
        dict: {fips: {'state': state, 'year': most_recent_upgrade_year, 'jurisdiction': name}}
    """
    # Separate baseline and upgrade records
    baselines = {}
    upgrades = {}

    for row in records:
        fips = row['FIPS']
        year = row['To_Year']
        info = {
            'state': row['State'],
            'year': year,
            'jurisdiction': row['Jurisdiction'],
        }

        if row['Transition_Type'] == 'baseline':
            baselines[fips] = info
        elif row['Transition_Type'] in UPGRADE_TYPES:
            if fips not in upgrades or year > upgrades[fips]['year']:
                upgrades[fips] = info

    # Use upgrade year if available, otherwise baseline year
    result = {}
    for fips in set(baselines.keys()) | set(upgrades.keys()):
        if fips in upgrades:
            result[fips] = upgrades[fips]
        elif fips in baselines:
            result[fips] = baselines[fips]

    return result


def group_by_state(most_recent):
    """
    Group jurisdictions by state.

    Args:
        most_recent: dict from get_most_recent_upgrades

    Returns:
        dict: {state: [list of upgrade years]}
    """
    by_state = defaultdict(list)
    for fips, data in most_recent.items():
        by_state[data['state']].append(data['year'])

    return by_state


def create_state_chart(state, years_list, output_path):
    """
    Create bar chart showing recency distribution for a state.

    Args:
        state: State name
        years_list: List of most recent upgrade years for jurisdictions
        output_path: Path to save chart
    """
    # Count by year, with pre-2006 bucket
    year_counts = defaultdict(int)
    pre_2006_count = 0
    for year in years_list:
        if year < 2006:
            pre_2006_count += 1
        else:
            year_counts[year] += 1

    # Get counts: pre-2006 bucket + standard years
    counts = [pre_2006_count] + [year_counts.get(y, 0) for y in CHART_YEARS]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))

    # Create bar chart with color gradient (older = red, newer = green)
    colors = plt.cm.RdYlGn(np.linspace(0.1, 0.9, len(CHART_LABELS)))
    bars = ax.bar(range(len(CHART_LABELS)), counts, color=colors,
                  edgecolor='black', linewidth=0.5)

    # Labels and title
    ax.set_xlabel('Year of Most Recent Upgrade', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Jurisdictions', fontsize=12, fontweight='bold')

    n_total = len(years_list)
    median_year = int(np.median(years_list))
    abbrev = STATE_ABBREVS.get(state, state[:2].upper())

    title = f'{state} ({abbrev}): Equipment Upgrade Recency'
    subtitle = f'n={n_total:,} jurisdictions | Median: {median_year}'
    ax.set_title(f'{title}\n{subtitle}', fontsize=14, fontweight='bold', pad=15)

    # X-axis labels
    ax.set_xticks(range(len(CHART_LABELS)))
    ax.set_xticklabels(CHART_LABELS, rotation=45, ha='right')

    # Grid
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Add value labels on bars with counts > 0
    max_height = max(counts) if counts else 1
    for i, count in enumerate(counts):
        if count > 0:
            ax.text(i, count + max_height * 0.02, str(count),
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Layout
    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def create_national_chart(most_recent, output_path):
    """
    Create bar chart showing recency distribution for all jurisdictions nationally.

    Args:
        most_recent: dict from get_most_recent_upgrades
        output_path: Path to save chart
    """
    # Collect all years
    all_years = [data['year'] for data in most_recent.values()]

    # Count by year, with pre-2006 bucket
    year_counts = defaultdict(int)
    pre_2006_count = 0
    for year in all_years:
        if year < 2006:
            pre_2006_count += 1
        else:
            year_counts[year] += 1

    # Get counts: pre-2006 bucket + standard years
    counts = [pre_2006_count] + [year_counts.get(y, 0) for y in CHART_YEARS]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 7))

    # Create bar chart with color gradient (older = red, newer = green)
    colors = plt.cm.RdYlGn(np.linspace(0.1, 0.9, len(CHART_LABELS)))
    bars = ax.bar(range(len(CHART_LABELS)), counts, color=colors,
                  edgecolor='black', linewidth=0.5)

    # Labels and title
    ax.set_xlabel('Year of Most Recent System Upgrade', fontsize=13, fontweight='bold')
    ax.set_ylabel('Number of Jurisdictions', fontsize=13, fontweight='bold')

    n_total = len(all_years)
    median_year = int(np.median(all_years))
    mean_year = np.mean(all_years)

    title = "Jurisdictions' Last Major Upgrade Year"
    subtitle = f'n={n_total:,} jurisdictions | Median: {median_year} | Mean: {mean_year:.1f}'
    ax.set_title(f'{title}\n{subtitle}', fontsize=15, fontweight='bold', pad=15)

    # X-axis labels
    ax.set_xticks(range(len(CHART_LABELS)))
    ax.set_xticklabels(CHART_LABELS, rotation=45, ha='right')

    # Grid
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Add value labels on bars
    max_height = max(counts) if counts else 1
    for i, count in enumerate(counts):
        if count > 0:
            ax.text(i, count + max_height * 0.02, f'{count:,}',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Layout
    plt.tight_layout()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  National chart saved to {output_path}")


def calculate_state_stats(by_state):
    """
    Calculate statistics for each state.

    Args:
        by_state: dict from group_by_state

    Returns:
        list of dicts with state stats, sorted by median year (oldest first)
    """
    stats = []
    for state, years in by_state.items():
        if not years:
            continue

        years_arr = np.array(years)
        median_year = np.median(years_arr)
        mean_year = np.mean(years_arr)
        std_year = np.std(years_arr)
        median_age = 2026 - median_year

        stats.append({
            'state': state,
            'abbrev': STATE_ABBREVS.get(state, state[:2].upper()),
            'n_jurisdictions': len(years),
            'median_year': median_year,
            'mean_year': mean_year,
            'std_year': std_year,
            'median_age': median_age,
        })

    # Sort by median year ascending (oldest first)
    stats.sort(key=lambda x: x['median_year'])

    return stats


def write_summary_report(stats, output_path):
    """
    Write summary report with state statistics.

    Args:
        stats: List of state stat dicts
        output_path: Path to save report
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=" * 90 + "\n")
        f.write("STATE EQUIPMENT RECENCY REPORT\n")
        f.write("=" * 90 + "\n")
        f.write("\n")
        f.write("How recently did jurisdictions in each state upgrade their voting equipment?\n")
        f.write("(Upgrades = vendor changes or system upgrades within same vendor)\n")
        f.write("\n")
        f.write("Sorted by median upgrade year (oldest first = states with most dated equipment)\n")
        f.write("\n")
        f.write("-" * 90 + "\n")
        f.write(f"{'Rank':<6}{'State':<25}{'N':<8}{'Median':<10}{'Mean':<10}{'Std Dev':<10}{'Median Age':<12}\n")
        f.write("-" * 90 + "\n")

        for i, s in enumerate(stats, 1):
            f.write(f"{i:<6}{s['state']:<25}{s['n_jurisdictions']:<8}"
                    f"{s['median_year']:<10.0f}{s['mean_year']:<10.1f}"
                    f"{s['std_year']:<10.1f}{s['median_age']:.0f} years\n")

        f.write("-" * 90 + "\n")
        f.write("\n")

        # Summary statistics
        all_medians = [s['median_year'] for s in stats]
        oldest = stats[0]
        newest = stats[-1]

        f.write("SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total states analyzed: {len(stats)}\n")
        f.write(f"Oldest median upgrade: {oldest['state']} ({oldest['median_year']:.0f})\n")
        f.write(f"Newest median upgrade: {newest['state']} ({newest['median_year']:.0f})\n")
        f.write(f"National median of state medians: {np.median(all_medians):.0f}\n")
        f.write("\n")
        f.write("=" * 90 + "\n")


def main():
    """Main execution function."""
    print("=" * 80)
    print("STATE EQUIPMENT RECENCY ANALYSIS")
    print("=" * 80)
    print()

    # Load data
    print("Loading jurisdiction transitions...")
    records = load_transitions()
    print(f"  Loaded {len(records):,} total transition records")

    # Get most recent upgrades
    print("Finding most recent upgrade for each jurisdiction...")
    most_recent = get_most_recent_upgrades(records)
    print(f"  Found {len(most_recent):,} jurisdictions with upgrade history")

    # Group by state
    print("Grouping by state...")
    by_state = group_by_state(most_recent)
    print(f"  Found {len(by_state)} states")
    print()

    # Generate national chart
    print("Generating national recency chart...")
    national_path = EQUIPMENT_FIGURES_DIR / 'national_system_recency.png'
    create_national_chart(most_recent, national_path)
    print()

    # Generate per-state charts
    print("Generating per-state charts...")
    chart_count = 0
    for state, years in sorted(by_state.items()):
        abbrev = STATE_ABBREVS.get(state, state[:2].upper())
        output_path = FIGURES_DIR / f'{abbrev}_recency.png'
        create_state_chart(state, years, output_path)
        chart_count += 1
        print(f"  {abbrev}: {len(years):,} jurisdictions")

    print(f"  Generated {chart_count} charts in {FIGURES_DIR}")
    print()

    # Calculate state statistics
    print("Calculating state statistics...")
    stats = calculate_state_stats(by_state)

    # Write summary report
    report_path = REPORTS_DIR / 'state_equipment_recency.txt'
    write_summary_report(stats, report_path)
    print(f"  Summary report saved to {report_path}")
    print()

    # Print top 10 oldest and newest
    print("States with OLDEST equipment (longest since upgrade):")
    for i, s in enumerate(stats[:10], 1):
        print(f"  {i:2}. {s['state']:<20} median upgrade: {s['median_year']:.0f} "
              f"({s['median_age']:.0f} years ago)")

    print()
    print("States with NEWEST equipment (most recent upgrades):")
    for i, s in enumerate(reversed(stats[-10:]), 1):
        print(f"  {i:2}. {s['state']:<20} median upgrade: {s['median_year']:.0f} "
              f"({s['median_age']:.0f} years ago)")

    print()
    print("=" * 80)
    print("STATE RECENCY ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
