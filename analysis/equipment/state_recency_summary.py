#!/usr/bin/env python3
"""
Generate state-level summary spreadsheet of equipment recency data.

Outputs a CSV with per-state counts of:
- Total jurisdictions
- Jurisdictions with last system upgrade <= 2018, 2016, 2014, 2012
- Jurisdictions with Dominion as vendor in 2026
- Jurisdictions with "previous generation" equipment

Also prints a report of what equipment is classified as "previous generation"
for review and refinement.

Reads from:
- data/processed/jurisdictions_time_series.csv (2026 equipment/vendor data)
- data/processed/jurisdiction_transitions.csv (upgrade history)

Outputs:
- outputs/reports/state_recency_summary.csv
"""

import csv
import statistics
import sys
from pathlib import Path
from collections import defaultdict

# Directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'processed'
REPORTS_DIR = PROJECT_ROOT / 'outputs' / 'reports'

# Transition types that count as "upgrades" (matches state_recency.py)
UPGRADE_TYPES = {'vendor', 'system'}

# Current generation equipment patterns
# Equipment matching ANY of these patterns is "current generation"
CURRENT_GEN_PATTERNS = [
    'ImageCast',           # Dominion ImageCast family
    'DS200',               # ES&S DS200
    'DS300',               # ES&S DS300
    'DS Central',          # ES&S DS Central
    'ExpressVote',         # ES&S BMD
    'Verity',              # Hart InterCivic Verity
    'Vanguard',            # Hart InterCivic Vanguard
    'Unisyn OpenElect F',  # Unisyn Gen 2 (FVS, FVT)
    'Clear Ballot',        # Clear Ballot
    'VotingWorks',         # VotingWorks
    'VSAP',                # Los Angeles County VSAP
]


def classify_generation(equipment, voting_class=None):
    """
    Classify equipment as 'current' or 'previous' generation.

    Args:
        equipment: Primary_Voting_Equipment string
        voting_class: Voting_Class string (optional)

    Returns:
        'current' or 'previous'
    """
    # Hand Count jurisdictions are considered current generation
    if voting_class == 'Hand Count':
        return 'current'

    if not equipment:
        return 'previous'

    for pattern in CURRENT_GEN_PATTERNS:
        if pattern in equipment:
            return 'current'
    return 'previous'


def load_2026_jurisdictions():
    """
    Load jurisdiction data for 2026.

    Returns:
        dict: {fips: {'state': str, 'jurisdiction': str, 'vendor': str,
                      'equipment': str, 'voting_class': str}}
    """
    filepath = DATA_DIR / 'jurisdictions_time_series.csv'

    if not filepath.exists():
        raise FileNotFoundError(f"Time series file not found: {filepath}")

    jurisdictions = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Year'] != '2026':
                continue

            fips = row['FIPS']
            # Parse registered voters, defaulting to 0 if empty/invalid
            try:
                reg_voters = int(row['Registered_Voters']) if row['Registered_Voters'] else 0
            except ValueError:
                reg_voters = 0

            jurisdictions[fips] = {
                'state': row['State'],
                'jurisdiction': row['Jurisdiction'],
                'vendor': row['Primary_Voting_Vendor'],
                'equipment': row['Primary_Voting_Equipment'],
                'voting_class': row['Voting_Class'],
                'registered_voters': reg_voters,
            }

    return jurisdictions


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
        dict: {fips: upgrade_year}
    """
    # Separate baseline and upgrade records
    baselines = {}
    upgrades = {}

    for row in records:
        fips = row['FIPS']
        year = row['To_Year']

        if row['Transition_Type'] == 'baseline':
            baselines[fips] = year
        elif row['Transition_Type'] in UPGRADE_TYPES:
            if fips not in upgrades or year > upgrades[fips]:
                upgrades[fips] = year

    # Use upgrade year if available, otherwise baseline year
    result = {}
    for fips in set(baselines.keys()) | set(upgrades.keys()):
        if fips in upgrades:
            result[fips] = upgrades[fips]
        elif fips in baselines:
            result[fips] = baselines[fips]

    return result


def calculate_state_summary(jurisdictions_2026, upgrade_years):
    """
    Calculate summary statistics for each state.

    Args:
        jurisdictions_2026: dict from load_2026_jurisdictions
        upgrade_years: dict from get_most_recent_upgrades

    Returns:
        list of dicts with state summary data, sorted alphabetically
    """
    # Group jurisdictions by state
    by_state = defaultdict(list)
    for fips, data in jurisdictions_2026.items():
        by_state[data['state']].append({
            'fips': fips,
            'vendor': data['vendor'],
            'equipment': data['equipment'],
            'voting_class': data['voting_class'],
            'upgrade_year': upgrade_years.get(fips),
            'registered_voters': data['registered_voters'],
        })

    # Calculate stats for each state
    stats = []
    for state, jurisdictions in sorted(by_state.items()):
        n_total = len(jurisdictions)
        v_total = sum(j['registered_voters'] for j in jurisdictions)

        n_2018 = sum(1 for j in jurisdictions
                     if j['upgrade_year'] and j['upgrade_year'] <= 2018)
        v_2018 = sum(j['registered_voters'] for j in jurisdictions
                     if j['upgrade_year'] and j['upgrade_year'] <= 2018)

        n_2016 = sum(1 for j in jurisdictions
                     if j['upgrade_year'] and j['upgrade_year'] <= 2016)
        v_2016 = sum(j['registered_voters'] for j in jurisdictions
                     if j['upgrade_year'] and j['upgrade_year'] <= 2016)

        n_2014 = sum(1 for j in jurisdictions
                     if j['upgrade_year'] and j['upgrade_year'] <= 2014)
        v_2014 = sum(j['registered_voters'] for j in jurisdictions
                     if j['upgrade_year'] and j['upgrade_year'] <= 2014)

        n_2012 = sum(1 for j in jurisdictions
                     if j['upgrade_year'] and j['upgrade_year'] <= 2012)
        v_2012 = sum(j['registered_voters'] for j in jurisdictions
                     if j['upgrade_year'] and j['upgrade_year'] <= 2012)

        n_dominion = sum(1 for j in jurisdictions
                         if j['vendor'] == 'Dominion')
        v_dominion = sum(j['registered_voters'] for j in jurisdictions
                         if j['vendor'] == 'Dominion')

        n_prev_gen = sum(1 for j in jurisdictions
                         if classify_generation(j['equipment'],
                                                j['voting_class']) == 'previous')
        v_prev_gen = sum(j['registered_voters'] for j in jurisdictions
                         if classify_generation(j['equipment'],
                                                j['voting_class']) == 'previous')

        # Calculate median upgrade year for jurisdictions with upgrade history
        years_with_upgrades = [j['upgrade_year'] for j in jurisdictions
                               if j['upgrade_year'] is not None]
        median_year = (statistics.median(years_with_upgrades)
                       if years_with_upgrades else None)

        stats.append({
            'state': state,
            'total': n_total,
            'total_voters': v_total,
            'median_upgrade_year': median_year,
            'upgrade_2018': n_2018,
            'upgrade_2018_voters': v_2018,
            'upgrade_2016': n_2016,
            'upgrade_2016_voters': v_2016,
            'upgrade_2014': n_2014,
            'upgrade_2014_voters': v_2014,
            'upgrade_2012': n_2012,
            'upgrade_2012_voters': v_2012,
            'dominion': n_dominion,
            'dominion_voters': v_dominion,
            'prev_gen': n_prev_gen,
            'prev_gen_voters': v_prev_gen,
        })

    return stats


def get_previous_gen_breakdown(jurisdictions_2026):
    """
    Get breakdown of previous generation equipment.

    Args:
        jurisdictions_2026: dict from load_2026_jurisdictions

    Returns:
        dict: {equipment: count} for previous gen equipment
    """
    prev_gen = defaultdict(int)
    for data in jurisdictions_2026.values():
        equipment = data['equipment']
        voting_class = data['voting_class']
        if classify_generation(equipment, voting_class) == 'previous':
            prev_gen[equipment] += 1

    return dict(sorted(prev_gen.items(), key=lambda x: -x[1]))


def write_csv(stats, output_path):
    """Write summary CSV file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'State',
            'Total_Jurisdictions',
            'Total_Registered_Voters',
            'Median_Upgrade_Year',
            'Upgrade_2018_Or_Earlier',
            'Upgrade_2018_Or_Earlier_Voters',
            'Upgrade_2016_Or_Earlier',
            'Upgrade_2016_Or_Earlier_Voters',
            'Upgrade_2014_Or_Earlier',
            'Upgrade_2014_Or_Earlier_Voters',
            'Upgrade_2012_Or_Earlier',
            'Upgrade_2012_Or_Earlier_Voters',
            'Dominion_Vendor_2026',
            'Dominion_Vendor_2026_Voters',
            'Previous_Gen_2026',
            'Previous_Gen_2026_Voters',
        ])

        for s in stats:
            median_str = (f"{s['median_upgrade_year']:.0f}"
                          if s['median_upgrade_year'] else '')
            writer.writerow([
                s['state'],
                s['total'],
                s['total_voters'],
                median_str,
                s['upgrade_2018'],
                s['upgrade_2018_voters'],
                s['upgrade_2016'],
                s['upgrade_2016_voters'],
                s['upgrade_2014'],
                s['upgrade_2014_voters'],
                s['upgrade_2012'],
                s['upgrade_2012_voters'],
                s['dominion'],
                s['dominion_voters'],
                s['prev_gen'],
                s['prev_gen_voters'],
            ])


def main():
    """Main execution function."""
    print("=" * 80)
    print("STATE EQUIPMENT RECENCY SUMMARY")
    print("=" * 80)
    print()

    # Load data
    print("Loading 2026 jurisdiction data...")
    jurisdictions_2026 = load_2026_jurisdictions()
    print(f"  Loaded {len(jurisdictions_2026):,} jurisdictions")

    print("Loading transition history...")
    records = load_transitions()
    print(f"  Loaded {len(records):,} transition records")

    print("Finding most recent upgrade for each jurisdiction...")
    upgrade_years = get_most_recent_upgrades(records)
    print(f"  Found {len(upgrade_years):,} jurisdictions with upgrade history")
    print()

    # Calculate summary
    print("Calculating state summaries...")
    stats = calculate_state_summary(jurisdictions_2026, upgrade_years)
    print(f"  Processed {len(stats)} states")
    print()

    # Write CSV
    output_path = REPORTS_DIR / 'state_recency_summary.csv'
    write_csv(stats, output_path)
    print(f"CSV saved to: {output_path}")
    print()

    # Print previous generation breakdown
    print("=" * 80)
    print("PREVIOUS GENERATION EQUIPMENT (for review)")
    print("=" * 80)
    print()
    print("Equipment classified as 'previous generation' in 2026:")
    print()

    prev_gen = get_previous_gen_breakdown(jurisdictions_2026)
    if prev_gen:
        for equipment, count in prev_gen.items():
            label = equipment if equipment else "(empty/unknown)"
            print(f"  {count:>4}  {label}")
        print()
        total_prev = sum(prev_gen.values())
        print(f"  Total previous generation: {total_prev:,} jurisdictions")
    else:
        print("  No previous generation equipment found.")

    print()
    print("=" * 80)
    print("SUMMARY COMPLETE")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
