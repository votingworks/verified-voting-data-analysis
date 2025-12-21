#!/usr/bin/env python3
"""
Analyze trends in Election Day Marking Methods and Tabulation across all years (2006-2026).

Creates 100% stacked bar charts showing how the proportions of different
marking methods and tabulation methods change over time.

Uses jurisdictions_time_series.csv as the data source, which includes
pre-computed Primary_Marking_Method and Accessible_Marking_Method fields.
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'trends'
TIME_SERIES_PATH = PROJECT_ROOT / 'data' / 'processed' / 'jurisdictions_time_series.csv'

YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]

# Cache for time series data
_time_series_cache = None


def load_time_series():
    """
    Load jurisdictions_time_series.csv (cached).

    Returns:
        list: List of row dicts from the CSV
    """
    global _time_series_cache
    if _time_series_cache is not None:
        return _time_series_cache

    print("Loading jurisdictions_time_series.csv...")
    with open(TIME_SERIES_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        _time_series_cache = list(reader)

    print(f"  Loaded {len(_time_series_cache):,} rows")
    return _time_series_cache


def load_field_by_year(field_name):
    """
    Load a specific field with registered voter counts for all jurisdictions across all years.

    Uses jurisdictions_time_series.csv as the data source.

    Args:
        field_name: Name of the field to load (e.g., 'Primary_Marking_Method')

    Returns:
        dict: {year: [(value, voters), (value, voters), ...]}
    """
    rows = load_time_series()
    field_by_year = defaultdict(list)

    for row in rows:
        year = int(row['Year'])
        value = row.get(field_name, '').strip()
        voters_str = row.get('Registered_Voters', '0').strip()

        # Parse voters (handle empty/non-numeric)
        try:
            voters = int(voters_str.replace(',', '')) if voters_str else 0
        except ValueError:
            voters = 0

        if value:  # Only include rows with valid field value
            field_by_year[year].append((value, voters))

    # Print summary
    for year in YEARS:
        data = field_by_year.get(year, [])
        unique_values = len(set(value for value, _ in data))
        print(f"✓ {year}: {len(data):,} jurisdictions, {unique_values} unique values")

    return dict(field_by_year)


def calculate_percentages(field_data_by_year, by='jurisdiction'):
    """
    Calculate percentages either by jurisdiction count or voter weight.

    Args:
        field_data_by_year: {year: [(value, voters), ...]}
        by: 'jurisdiction' or 'voters'

    Returns:
        dict: {year: {value: percentage, ...}}
    """
    percentages_by_year = {}

    for year, data in field_data_by_year.items():
        if by == 'jurisdiction':
            # Count jurisdictions
            value_counts = Counter(value for value, voters in data)
            total = sum(value_counts.values())
            percentages = {v: (count/total*100) for v, count in value_counts.items()}

        elif by == 'voters':
            # Sum registered voters per value
            voter_sums = defaultdict(int)
            for value, voters in data:
                voter_sums[value] += voters

            total_voters = sum(voter_sums.values())
            percentages = {v: (voters/total_voters*100) if total_voters > 0 else 0
                          for v, voters in voter_sums.items()}

        percentages_by_year[year] = percentages

    return percentages_by_year


def create_stacked_bar_chart(percentages_by_year, output_file, title, subtitle="", group_pattern=None, custom_colors=None):
    """
    Create a 100% stacked bar chart showing field value proportions over time.

    Args:
        percentages_by_year: dict mapping year to {value: percentage, ...}
        output_file: output filename for chart
        title: chart title
        subtitle: optional subtitle (e.g., "By Jurisdiction Count" or "Weighted by Registered Voters")
        group_pattern: optional string pattern to group matching items at bottom (e.g., "Hand marked")
        custom_colors: optional dict mapping value names to specific colors
    """

    # Get all unique values across all years
    all_values = set()
    for year_data in percentages_by_year.values():
        all_values.update(year_data.keys())

    # Sort values for consistent ordering (put common ones first)
    # Calculate average percentage across all years for sorting
    value_avg_pct = defaultdict(float)
    for year_data in percentages_by_year.values():
        for value, pct in year_data.items():
            value_avg_pct[value] += pct

    # Sort by average percentage (most common first)
    if group_pattern:
        # For marking method, use special multi-tier grouping
        if group_pattern == 'Hand marked':
            # Tier 1: Hand marked items (bottom)
            hand_marked = [v for v in value_avg_pct.keys() if v.startswith('Hand marked')]
            # Tier 2: BMD items
            bmd_items = [v for v in value_avg_pct.keys()
                        if v not in hand_marked and ('BMD' in v or 'Ballot Marking Device' in v)]
            # Tier 3: DREs with VVPAT (less problematic)
            dre_with_vvpat = [v for v in value_avg_pct.keys()
                             if v not in hand_marked and v not in bmd_items and 'DREs with VVPAT' in v]
            # Tier 4: DREs without VVPAT (more problematic - higher up to stand out)
            dre_without_vvpat = [v for v in value_avg_pct.keys()
                                if v not in hand_marked and v not in bmd_items and
                                v not in dre_with_vvpat and 'DREs without VVPAT' in v]
            # Tier 5: Everything else (top)
            other_items = [v for v in value_avg_pct.keys()
                          if v not in hand_marked and v not in bmd_items and
                          v not in dre_with_vvpat and v not in dre_without_vvpat]

            # Sort each tier by average percentage
            hand_marked_sorted = sorted(hand_marked, key=lambda v: value_avg_pct[v], reverse=True)
            bmd_sorted = sorted(bmd_items, key=lambda v: value_avg_pct[v], reverse=True)
            dre_vvpat_sorted = sorted(dre_with_vvpat, key=lambda v: value_avg_pct[v], reverse=True)
            dre_no_vvpat_sorted = sorted(dre_without_vvpat, key=lambda v: value_avg_pct[v], reverse=True)
            other_sorted = sorted(other_items, key=lambda v: value_avg_pct[v], reverse=True)

            # Stack from bottom to top: hand marked, BMDs, DREs with VVPAT, DREs without VVPAT, others
            sorted_values = hand_marked_sorted + bmd_sorted + dre_vvpat_sorted + dre_no_vvpat_sorted + other_sorted
        else:
            # Standard 2-tier grouping for other fields
            grouped = [v for v in value_avg_pct.keys() if v.startswith(group_pattern)]
            ungrouped = [v for v in value_avg_pct.keys() if not v.startswith(group_pattern)]

            grouped_sorted = sorted(grouped, key=lambda v: value_avg_pct[v], reverse=True)
            ungrouped_sorted = sorted(ungrouped, key=lambda v: value_avg_pct[v], reverse=True)

            sorted_values = grouped_sorted + ungrouped_sorted
    else:
        sorted_values = sorted(value_avg_pct.keys(), key=lambda v: value_avg_pct[v], reverse=True)

    # Prepare data for stacking
    years = sorted(percentages_by_year.keys())

    # Create matrix of percentages for plotting
    # Each row is a value, each column is a year
    percentages = {}
    for value in sorted_values:
        percentages[value] = []
        for year in years:
            pct = percentages_by_year[year].get(value, 0)
            percentages[value].append(pct)

    # Create the stacked bar chart
    fig, ax = plt.subplots(figsize=(14, 8))

    # Assign colors - use custom colors if provided, otherwise use colormap
    if custom_colors:
        # Default cool/neutral colors for items not in custom_colors
        # Interleaved palette of purple, blue, green, pink, and gray
        default_colors = [
            '#7B68EE',  # Medium slate blue (purple-blue)
            '#66CDAA',  # Medium aquamarine (green)
            '#778899',  # Light slate gray
            '#DDA0DD',  # Plum (pink-purple)
            '#4682B4',  # Steel blue
            '#8FBC8F',  # Dark sea green
            '#B0C4DE',  # Light steel blue
            '#98FB98',  # Pale green
            '#9999A8',  # Cool gray
            '#B19CD9',  # Wisteria (purple)
            '#87CEEB',  # Sky blue
            '#AFEEEE',  # Pale turquoise (blue-green)
            '#D8BFD8',  # Thistle (pink)
            '#5F9EA0',  # Cadet blue
            '#C8E6C9',  # Light green
        ]

        colors = []
        default_idx = 0
        for value in sorted_values:
            if value in custom_colors:
                colors.append(custom_colors[value])
            else:
                colors.append(default_colors[default_idx % len(default_colors)])
                default_idx += 1
    else:
        # Use standard colormap
        colors = plt.cm.tab20(np.linspace(0, 1, len(sorted_values)))

    # Create the stacked bars
    x = np.arange(len(years))
    width = 0.8
    bottom = np.zeros(len(years))

    bars = []
    for idx, value in enumerate(sorted_values):
        p = ax.bar(x, percentages[value], width, bottom=bottom,
                   label=value, color=colors[idx], edgecolor='white', linewidth=0.5)
        bars.append(p)
        bottom += percentages[value]

    # Customize the plot
    ax.set_xlabel('Year', fontsize=13, fontweight='bold')
    ax.set_ylabel('Percentage', fontsize=13, fontweight='bold')

    # Add title with optional subtitle
    full_title = title
    if subtitle:
        full_title = f"{title}\n{subtitle}"
    ax.set_title(full_title, fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(years)
    ax.set_ylim(0, 100)

    # Add percentage labels on y-axis
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_yticklabels(['0%', '20%', '40%', '60%', '80%', '100%'])

    # Add grid for readability
    ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)

    # Add legend - position based on number of items
    num_items = len(sorted_values)

    # For many items (>6), place legend below with 2 columns to limit width
    # Otherwise place on the right side
    if num_items > 6:
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.08),
                 fontsize=9, frameon=True, fancybox=True, shadow=True,
                 ncol=2)
    else:
        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5),
                 fontsize=9, frameon=True, fancybox=True, shadow=True)

    # Tight layout to prevent label cutoff
    plt.tight_layout()

    # Save figure
    output_path = Path(output_file)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Chart saved to {output_path}")

    plt.close()


def print_summary_table(field_by_year, field_name):
    """Print a summary table showing counts and percentages by year."""

    print("\n" + "=" * 120)
    print(f"SUMMARY TABLE: Jurisdictions by {field_name}")
    print("=" * 120)
    print()

    # Get all unique values
    all_values = set()
    for counter in field_by_year.values():
        all_values.update(counter.keys())

    # Calculate totals for sorting
    value_totals = Counter()
    for counter in field_by_year.values():
        value_totals.update(counter)

    sorted_values = [value for value, _ in value_totals.most_common()]
    years = sorted(field_by_year.keys())

    # Print header
    header = f"{field_name:<60} | " + " | ".join([f"{year}" for year in years])
    print(header)
    print("-" * 120)

    # Print each value
    for value in sorted_values:
        row = f"{value:<60} |"
        for year in years:
            total = sum(field_by_year[year].values())
            count = field_by_year[year].get(value, 0)
            pct = (count / total * 100) if total > 0 else 0
            row += f" {count:>4} ({pct:>4.1f}%) |"
        print(row)

    # Print totals
    print("-" * 120)
    row = f"{'TOTAL':<60} |"
    for year in years:
        total = sum(field_by_year[year].values())
        row += f" {total:>4} (100.0%) |"
    print(row)
    print()


def analyze_field(field_name, field_display_name, output_prefix, group_pattern=None, custom_colors=None):
    """
    Analyze a single field with both weighting methods (jurisdiction count and registered voters).

    Args:
        field_name: CSV column name (e.g., 'Election Day Marking Method')
        field_display_name: Display name for output (e.g., 'Election Day Marking Method')
        output_prefix: Filename prefix for charts (e.g., 'marking_method')
        group_pattern: optional pattern to group items at bottom of stack (e.g., "Hand marked")
        custom_colors: optional dict mapping value names to specific colors
    """
    print("\n" + "=" * 80)
    print(f"ANALYZING: {field_display_name.upper()}")
    print("=" * 80)
    print()

    # Load data (values + voters)
    print(f"Loading {field_display_name} data for all years...")
    field_data = load_field_by_year(field_name)
    print(f"\n✓ Loaded data for {len(field_data)} years")

    # Generate jurisdiction-weighted chart
    print(f"\n  Generating chart by jurisdiction count...")
    pct_jurisdiction = calculate_percentages(field_data, by='jurisdiction')
    create_stacked_bar_chart(
        pct_jurisdiction,
        OUTPUT_DIR / f'{output_prefix}_jurisdiction_trends.png',
        f'{field_display_name} Trends (2006-2026)',
        subtitle='By Jurisdiction Count',
        group_pattern=group_pattern,
        custom_colors=custom_colors
    )

    # Generate voter-weighted chart
    print(f"  Generating chart weighted by registered voters...")
    pct_voters = calculate_percentages(field_data, by='voters')
    create_stacked_bar_chart(
        pct_voters,
        OUTPUT_DIR / f'{output_prefix}_voters_trends.png',
        f'{field_display_name} Trends (2006-2026)',
        subtitle='Weighted by Registered Voters',
        group_pattern=group_pattern,
        custom_colors=custom_colors
    )


def analyze_accessible_marking_method():
    """
    Generate charts showing accessible marking methods for HMPB systems only.

    Uses pre-computed Accessible_Marking_Method from jurisdictions_time_series.csv.
    Only includes rows where the field is non-empty (i.e., HMPB systems).
    """
    print("\n" + "=" * 80)
    print("ANALYZING: ACCESSIBLE MARKING METHOD (HMPB SYSTEMS)")
    print("=" * 80)
    print()

    # Load pre-computed Accessible_Marking_Method from time series
    # load_field_by_year only includes rows with non-empty values,
    # so non-HMPB systems (which have empty Accessible_Marking_Method) are filtered out
    print("Loading Accessible_Marking_Method data...")
    field_data = load_field_by_year('Accessible_Marking_Method')
    print(f"\n✓ Loaded data for {len(field_data)} years")

    # Custom colors for accessible methods - distinct from primary chart
    # Use same colors as simplified chart for matching categories
    accessible_colors = {
        'BMD': '#2E8B57',  # Sea green (matches Primary Marking Method)
        'DRE with VVPAT': '#DAA520',  # Goldenrod (matches simplified)
        'DRE without VVPAT': '#CD5C5C',  # Indian red (matches simplified)
        'None': '#778899',  # Light slate gray
        'Mixed': '#5F9EA0',  # Cadet blue
    }

    # Generate jurisdiction-weighted chart
    print("\n  Generating accessible method chart by jurisdiction count...")
    pct_jurisdiction = calculate_percentages(field_data, by='jurisdiction')
    create_stacked_bar_chart(
        pct_jurisdiction,
        OUTPUT_DIR / 'accessible_marking_method_jurisdiction_trends.png',
        'Accessible Marking Method Trends - HMPB Systems (2006-2026)',
        subtitle='By Jurisdiction Count',
        custom_colors=accessible_colors
    )

    # Generate voter-weighted chart
    print("  Generating accessible method chart weighted by registered voters...")
    pct_voters = calculate_percentages(field_data, by='voters')
    create_stacked_bar_chart(
        pct_voters,
        OUTPUT_DIR / 'accessible_marking_method_voters_trends.png',
        'Accessible Marking Method Trends - HMPB Systems (2006-2026)',
        subtitle='Weighted by Registered Voters',
        custom_colors=accessible_colors
    )


def analyze_simplified_marking_method():
    """
    Generate simplified marking method charts using pre-computed Primary_Marking_Method.

    Uses 6 categories from jurisdictions_time_series.csv:
    - Hand Marked Paper Ballots (all variants)
    - Punch Cards
    - BMD
    - DRE with VVPAT
    - DRE without VVPAT
    - Mechanical Lever Machine
    """
    print("\n" + "=" * 80)
    print("ANALYZING: PRIMARY MARKING METHOD")
    print("=" * 80)
    print()

    # Load pre-computed Primary_Marking_Method from time series
    print("Loading Primary_Marking_Method data...")
    field_data = load_field_by_year('Primary_Marking_Method')
    print(f"\n✓ Loaded data for {len(field_data)} years")

    # Custom colors for simplified categories - varied palette
    simplified_colors = {
        'Hand Marked Paper Ballots': '#4682B4',  # Steel blue
        'Punch Cards': '#9370DB',  # Medium purple
        'BMD': '#2E8B57',  # Sea green
        'DRE with VVPAT': '#DAA520',  # Goldenrod
        'DRE without VVPAT': '#CD5C5C',  # Indian red
        'Mechanical Lever Machine': '#708090',  # Slate gray
    }

    # Generate jurisdiction-weighted chart
    print("\n  Generating chart by jurisdiction count...")
    pct_jurisdiction = calculate_percentages(field_data, by='jurisdiction')
    create_stacked_bar_chart(
        pct_jurisdiction,
        OUTPUT_DIR / 'primary_marking_method_jurisdiction_trends.png',
        'Primary Marking Method Trends (2006-2026)',
        subtitle='By Jurisdiction Count',
        group_pattern='Hand Marked',
        custom_colors=simplified_colors
    )

    # Generate voter-weighted chart
    print("  Generating chart weighted by registered voters...")
    pct_voters = calculate_percentages(field_data, by='voters')
    create_stacked_bar_chart(
        pct_voters,
        OUTPUT_DIR / 'primary_marking_method_voters_trends.png',
        'Primary Marking Method Trends (2006-2026)',
        subtitle='Weighted by Registered Voters',
        group_pattern='Hand Marked',
        custom_colors=simplified_colors
    )


def main():
    """Main processing pipeline."""

    print("=" * 80)
    print("ELECTION DAY TRENDS ANALYSIS")
    print("=" * 80)

    # Analyze fields (using time series field names with underscores)
    analyze_field('Voting_Location', 'Voting Location', str(OUTPUT_DIR / 'voting_location'))
    analyze_field('All_Mail_Ballot', 'All Mail Ballot Status', str(OUTPUT_DIR / 'all_mail_ballot'))

    # Generate simplified marking method charts
    analyze_simplified_marking_method()

    # Generate accessible marking method charts (HMPB systems only)
    analyze_accessible_marking_method()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"\nGenerated chart files:")
    print(f"\nVoting Location:")
    print(f"  - voting_location_jurisdiction_trends.png")
    print(f"  - voting_location_voters_trends.png")
    print(f"\nAll Mail Ballot Status:")
    print(f"  - all_mail_ballot_jurisdiction_trends.png")
    print(f"  - all_mail_ballot_voters_trends.png")
    print(f"\nPrimary Marking Method (simplified):")
    print(f"  - primary_marking_method_jurisdiction_trends.png")
    print(f"  - primary_marking_method_voters_trends.png")
    print(f"\nAccessible Marking Method (HMPB systems):")
    print(f"  - accessible_marking_method_jurisdiction_trends.png")
    print(f"  - accessible_marking_method_voters_trends.png")
    print()


if __name__ == "__main__":
    main()
