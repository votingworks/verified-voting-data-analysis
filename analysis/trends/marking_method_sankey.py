#!/usr/bin/env python3
"""
Generate Sankey diagram showing marking method transitions between two years.

Shows how jurisdictions flowed between marking method categories
(e.g., DREs → BMDs, Hand marked → Hand marked).

Usage:
    python3 marking_method_sankey.py 2010 2026
    python3 marking_method_sankey.py 2006 2020

Args:
    start_year: First year to compare
    end_year: Second year to compare

Reads from: data/processed/jurisdictions_time_series.csv
Output: outputs/figures/trends/marking_method_transitions_{start}_{end}.png
"""

import sys
from pathlib import Path
from collections import Counter
import pandas as pd
import plotly.graph_objects as go

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
OUTPUT_DIR = PROJECT_ROOT / 'outputs' / 'figures' / 'trends'

# Category colors (matching jurisdiction_trends.py)
COLORS = {
    'Hand marked paper ballots': '#4682B4',  # Steel blue
    'DREs': '#CD5C5C',  # Indian red
    'Ballot Marking Devices': '#2E8B57',  # Sea green
}


def categorize_marking_method(value):
    """
    Map Primary_Marking_Method to 3 simplified categories.

    Returns None for values that should be excluded (lever machines, etc.)
    """
    if pd.isna(value) or not value:
        return None

    # Hand marked paper ballots (includes punch cards)
    if value in ('Hand Marked Paper Ballots', 'Punch Cards'):
        return 'Hand marked paper ballots'

    # Ballot Marking Devices
    if value == 'BMD':
        return 'Ballot Marking Devices'

    # DREs (combine with and without VVPAT)
    if value in ('DRE with VVPAT', 'DRE without VVPAT'):
        return 'DREs'

    # Exclude lever machines and other edge cases
    return None


def load_time_series():
    """Load the jurisdictions time series data."""
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    return pd.read_csv(filepath)


def load_jurisdiction_methods(df, year):
    """
    Get marking method data for a year from the time series.

    Args:
        df: Full time series DataFrame
        year: Year to extract

    Returns:
        dict: {fips: category} for valid jurisdictions
    """
    year_df = df[df['Year'] == year]

    methods = {}
    for _, row in year_df.iterrows():
        fips = row['FIPS']
        marking_method = row['Primary_Marking_Method']

        category = categorize_marking_method(marking_method)
        if category:
            methods[fips] = category

    return methods


def compute_transitions(start_methods, end_methods):
    """
    Compute transition counts between categories.

    Returns:
        dict: {(source_cat, target_cat): count}
        int: number of matched jurisdictions
    """
    transitions = Counter()
    matched = 0

    # Only count jurisdictions present in both years
    common_fips = set(start_methods.keys()) & set(end_methods.keys())

    for fips in common_fips:
        source = start_methods[fips]
        target = end_methods[fips]
        transitions[(source, target)] += 1
        matched += 1

    return dict(transitions), matched


def create_sankey_diagram(transitions, start_year, end_year, n_jurisdictions, output_path):
    """
    Create Sankey diagram showing category transitions.
    """
    # Define nodes (source categories on left, target categories on right)
    categories = ['Hand marked paper ballots', 'DREs', 'Ballot Marking Devices']

    # Short labels for display
    short_labels = {
        'Hand marked paper ballots': 'HMPBs',
        'DREs': 'DREs',
        'Ballot Marking Devices': 'BMDs',
    }

    # Node labels: left side = start year, right side = end year
    node_labels = [f"{short_labels[cat]} ({start_year})" for cat in categories] + \
                  [f"{short_labels[cat]} ({end_year})" for cat in categories]

    # Node colors
    node_colors = [COLORS[cat] for cat in categories] * 2

    # Build links from transitions
    sources = []
    targets = []
    values = []
    link_colors = []

    for (source_cat, target_cat), count in transitions.items():
        if count == 0:
            continue

        source_idx = categories.index(source_cat)
        target_idx = categories.index(target_cat) + len(categories)  # Offset for right side

        sources.append(source_idx)
        targets.append(target_idx)
        values.append(count)

        # Color link by source category (with transparency)
        base_color = COLORS[source_cat]
        # Convert hex to rgba
        r = int(base_color[1:3], 16)
        g = int(base_color[3:5], 16)
        b = int(base_color[5:7], 16)
        link_colors.append(f'rgba({r},{g},{b},0.5)')

    # Create figure
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=20,
            thickness=30,
            line=dict(color='black', width=1),
            label=node_labels,
            color=node_colors,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
        )
    )])

    # Update layout
    fig.update_layout(
        title=dict(
            text=f"Marking Method Transitions ({start_year} → {end_year})<br>"
                 f"<sup>n={n_jurisdictions:,} jurisdictions tracked</sup>",
            x=0.5,
            xanchor='center',
            font=dict(size=20),
        ),
        font=dict(size=14),
        width=1000,
        height=600,
    )

    # Save to PNG
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_image(str(output_path), scale=2)

    return fig


def main():
    """Main execution function."""
    print("=" * 80)
    print("MARKING METHOD TRANSITION ANALYSIS")
    print("=" * 80)
    print()

    # Ensure output directory exists early
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Parse arguments
    if len(sys.argv) < 3:
        print("Usage: python3 marking_method_transitions.py <start_year> <end_year>")
        print("Example: python3 marking_method_transitions.py 2010 2026")
        return 1

    start_year = int(sys.argv[1])
    end_year = int(sys.argv[2])

    print(f"Analyzing transitions: {start_year} → {end_year}")
    print()

    # Load data
    print("Loading jurisdictions time series...")
    df = load_time_series()
    print(f"✓ Loaded {len(df):,} records")

    print(f"Extracting {start_year} marking methods...")
    start_methods = load_jurisdiction_methods(df, start_year)
    print(f"✓ {len(start_methods):,} jurisdictions with valid marking method")

    print(f"Extracting {end_year} marking methods...")
    end_methods = load_jurisdiction_methods(df, end_year)
    print(f"✓ {len(end_methods):,} jurisdictions with valid marking method")
    print()

    # Compute transitions
    print("Computing transitions...")
    transitions, n_matched = compute_transitions(start_methods, end_methods)
    print(f"✓ {n_matched:,} jurisdictions present in both years")
    print()

    # Print transition matrix
    categories = ['Hand marked paper ballots', 'DREs', 'Ballot Marking Devices']
    print("Transition matrix:")
    print(f"{'From \\ To':<30}", end="")
    for cat in categories:
        print(f"{cat[:15]:>16}", end="")
    print()
    print("-" * 78)

    for source in categories:
        print(f"{source:<30}", end="")
        for target in categories:
            count = transitions.get((source, target), 0)
            print(f"{count:>16,}", end="")
        print()
    print()

    # Summary statistics
    stayed_same = sum(transitions.get((cat, cat), 0) for cat in categories)
    changed = n_matched - stayed_same
    print(f"Jurisdictions that stayed same: {stayed_same:,} ({stayed_same/n_matched*100:.1f}%)")
    print(f"Jurisdictions that changed: {changed:,} ({changed/n_matched*100:.1f}%)")
    print()

    # Generate Sankey diagram
    output_path = OUTPUT_DIR / f'marking_method_transitions_{start_year}_{end_year}.png'
    print("Generating Sankey diagram...")
    create_sankey_diagram(transitions, start_year, end_year, n_matched, output_path)
    print(f"✓ Chart saved to {output_path}")

    print()
    print("=" * 80)
    print("✓ TRANSITION ANALYSIS COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
