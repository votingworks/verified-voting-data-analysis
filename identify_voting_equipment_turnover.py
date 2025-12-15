#!/usr/bin/env python3
"""
Analyze equipment renewals and changes over time (2006-2026).

Tracks two types of equipment changes:
1. Between-system: When voting system family changes (e.g., ES&S DS200 → Dominion ImageCast)
2. Within-system: When equipment changes but system stays same (e.g., ES&S DS200 → ES&S ExpressVote)

For each change, records:
- Year of change
- Equipment, system, vendor, marking method before and after
- DRE status and marking method status transitions
- Vendor retention and years between changes

Outputs:
- between_system_turnovers.csv - System family changed
- within_system_turnovers.csv - Equipment changed, same system family
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict


YEARS = [2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024, 2026]


def load_all_years():
    """
    Load equipment data for all years (2006-2026).

    Returns:
        dict: {year: {fips: {state, jurisdiction, equipment, vendor, first_year}}}
    """
    data_by_year = {}

    for year in YEARS:
        filepath = f'data/verifier-condensed/{year}_verifier-jurisdictions-condensed.csv'

        if not Path(filepath).exists():
            print(f"Warning: {filepath} not found, skipping...")
            continue

        data_by_year[year] = {}

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            reader = csv.DictReader(lines[1:])  # Skip title row

            for row in reader:
                fips = row['FIPS code']
                data_by_year[year][fips] = {
                    'state': row['State'],
                    'jurisdiction': row['Jurisdiction'],
                    'equipment': row['Primary Voting Equipment'].strip(),
                    'vendor': row['Primary Voting Vendor'].strip(),
                    'family': row.get('Primary Voting System', '').strip(),
                    'first_year': row.get('Primary Voting Equipment - First Year In Use', '').strip(),
                    'is_dre': row.get('DRE?', '').strip(),
                    'marking_method': row.get('Primary Marking Method', '').strip()
                }

    return data_by_year


def initialize_baselines(data_2006):
    """
    Initialize jurisdiction timelines with 2006 baseline.

    For each jurisdiction in 2006:
    - If "Primary Voting Equipment - First Year In Use" is populated and valid → use that year as baseline
    - If empty, invalid, or unreasonable (< 1980 or > 2026) → use 2006 as baseline

    Returns:
        dict: {fips: {state, jurisdiction, timeline: [baseline_entry]}}
    """
    timelines = {}

    for fips, data in data_2006.items():
        first_year_str = data['first_year']

        # Use first_year if available and valid, otherwise use 2006
        try:
            year = int(first_year_str) if first_year_str else 2006
            # Take absolute value (negative years are data entry errors)
            year = abs(year)
            # Validate year is reasonable (voting equipment systems post-1980)
            if year < 1950 or year > 2026:
                baseline_year = 2006
            else:
                baseline_year = year
        except ValueError:
            baseline_year = 2006

        timelines[fips] = {
            'state': data['state'],
            'jurisdiction': data['jurisdiction'],
            'timeline': [{
                'year': baseline_year,
                'equipment': data['equipment'],
                'vendor': data['vendor'],
                'family': data['family'],
                'is_dre': data.get('is_dre', ''),
                'marking_method': data.get('marking_method', ''),
                'is_baseline': True
            }]
        }

    return timelines


def detect_changes(timelines, data_by_year, years):
    """
    Walk through years sequentially, detecting equipment changes.

    For each year pair (year_from → year_to):
        For each jurisdiction:
            If equipment system changed:
                Add "Between System" change entry to timeline
            Elif equipment changed (but system stayed same):
                Add "Within System" change entry to timeline

    Modifies timelines in place.
    """
    for i in range(len(years) - 1):
        year_from = years[i]
        year_to = years[i + 1]

        # Skip if either year's data is missing
        if year_from not in data_by_year or year_to not in data_by_year:
            continue

        for fips in timelines:
            # Get current equipment (last entry in timeline)
            current = timelines[fips]['timeline'][-1]

            # Get equipment in year_to (if jurisdiction still exists)
            if fips in data_by_year[year_to]:
                new_data = data_by_year[year_to][fips]

                # Determine what changed
                if new_data['family'] != current['family']:
                    # Between-system change (system family changed)
                    change_type = 'Between System'
                elif new_data['equipment'] != current['equipment']:
                    # Within-system change (equipment changed but system stayed same)
                    change_type = 'Within System'
                else:
                    # No change
                    change_type = None

                # Only add timeline entry if something changed
                if change_type:
                    timelines[fips]['timeline'].append({
                        'year': year_to,
                        'equipment': new_data['equipment'],
                        'vendor': new_data['vendor'],
                        'family': new_data['family'],
                        'is_dre': new_data.get('is_dre', ''),
                        'marking_method': new_data.get('marking_method', ''),
                        'change_type': change_type,
                        'is_baseline': False
                    })


def calculate_dre_status(from_is_dre, to_is_dre):
    """
    Calculate DRE status transition between two equipment changes.

    Args:
        from_is_dre: DRE status of original equipment ("Yes", "No", or "")
        to_is_dre: DRE status of new equipment ("Yes", "No", or "")

    Returns:
        str: "To DRE", "From DRE", "No Change", or "" if data is missing
    """
    # Handle missing data
    if not from_is_dre or not to_is_dre:
        return ""

    # Normalize to boolean for comparison
    from_dre = (from_is_dre == "Yes")
    to_dre = (to_is_dre == "Yes")

    # Determine transition
    if not from_dre and to_dre:
        return "To DRE"
    elif from_dre and not to_dre:
        return "From DRE"
    else:
        return "No Change"


def calculate_marking_method_status(from_marking_method, to_marking_method):
    """
    Calculate marking method transition between two equipment changes.

    Args:
        from_marking_method: Marking method of original equipment ("Paper", "Machine", or "")
        to_marking_method: Marking method of new equipment ("Paper", "Machine", or "")

    Returns:
        str: "To Machine", "To Paper", "No Change", or "" if data is missing
    """
    # Handle missing data
    if not from_marking_method or not to_marking_method:
        return ""

    # Normalize for comparison
    from_method = from_marking_method.strip()
    to_method = to_marking_method.strip()

    # Determine transition
    if from_method == to_method:
        return "No Change"
    elif to_method == "Machine":
        return "To Machine"
    elif to_method == "Paper":
        return "To Paper"
    else:
        return "Changed"  # Fallback for unexpected values


def generate_two_csv_files(timelines, between_output_file, within_output_file):
    """
    Convert timelines to two CSV files: between-system and within-system changes.

    For each jurisdiction with multiple timeline entries:
        For each change (entry[i] → entry[i+1]):
            Categorize as between-system or within-system
            Write row with before/after data to appropriate file

    Returns:
        tuple: (num_between_changes, num_within_changes)
    """
    between_changes = []
    within_changes = []

    for fips, data in timelines.items():
        timeline = data['timeline']

        # Skip jurisdictions with no changes
        if len(timeline) <= 1:
            continue

        # For each pair of consecutive entries
        for i in range(len(timeline) - 1):
            from_entry = timeline[i]
            to_entry = timeline[i + 1]

            change_dict = {
                'FIPS': fips,
                'State': data['state'],
                'Jurisdiction': data['jurisdiction'],
                'From_Year': from_entry['year'],
                'From_Equipment': from_entry['equipment'],
                'From_Vendor': from_entry['vendor'],
                'From_System': from_entry['family'],
                'From_DRE': from_entry.get('is_dre', ''),
                'From_Marking_Method': from_entry.get('marking_method', ''),
                'To_Year': to_entry['year'],
                'To_Equipment': to_entry['equipment'],
                'To_Vendor': to_entry['vendor'],
                'To_System': to_entry['family'],
                'To_DRE': to_entry.get('is_dre', ''),
                'To_Marking_Method': to_entry.get('marking_method', ''),
                'DRE_Status': calculate_dre_status(
                    from_entry.get('is_dre', ''),
                    to_entry.get('is_dre', '')
                ),
                'Marking_Method_Status': calculate_marking_method_status(
                    from_entry.get('marking_method', ''),
                    to_entry.get('marking_method', '')
                ),
                'Vendor_Retained': from_entry['vendor'] == to_entry['vendor'],
                'Years_Between': to_entry['year'] - from_entry['year'],
                'From_Baseline': from_entry['is_baseline']
            }

            # Separate by change type
            change_type = to_entry.get('change_type', 'Between System')
            if change_type == 'Between System':
                between_changes.append(change_dict)
            elif change_type == 'Within System':
                within_changes.append(change_dict)

    # Write both CSV files
    fieldnames = [
        'FIPS', 'State', 'Jurisdiction',
        'From_Year', 'From_Equipment', 'From_Vendor', 'From_System', 'From_DRE', 'From_Marking_Method',
        'To_Year', 'To_Equipment', 'To_Vendor', 'To_System', 'To_DRE', 'To_Marking_Method',
        'DRE_Status', 'Marking_Method_Status', 'Vendor_Retained', 'Years_Between', 'From_Baseline'
    ]

    # Write between-system changes
    with open(between_output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(between_changes)

    # Write within-system changes
    with open(within_output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(within_changes)

    return len(between_changes), len(within_changes)


def generate_no_turnover_csv(timelines, output_file):
    """
    Generate CSV of jurisdictions with no equipment system changes (2006-2026).

    Filters: Excludes Hand Count jurisdictions only.

    CSV Schema: Matches between_system_turnovers.csv for easy merging
    """
    no_turnover_rows = []

    for fips, data in timelines.items():
        timeline = data['timeline']

        # Only process jurisdictions with no changes
        if len(timeline) != 1:
            continue

        baseline = timeline[0]

        # FILTER: Exclude Hand Count only
        if baseline['equipment'] == 'Hand Count':
            continue

        # Calculate lifecycle from baseline to 2026
        from_year = baseline['year']
        to_year = 2026
        years_between = to_year - from_year

        # Skip invalid lifecycles
        if years_between < 0:
            continue

        row = {
            'FIPS': fips,
            'State': data['state'],
            'Jurisdiction': data['jurisdiction'],
            'From_Year': from_year,
            'From_Equipment': baseline['equipment'],
            'From_Vendor': baseline['vendor'],
            'From_System': baseline['family'],
            'From_DRE': baseline.get('is_dre', ''),
            'From_Marking_Method': baseline.get('marking_method', ''),
            'To_Year': to_year,
            'To_Equipment': baseline['equipment'],  # Same (no change)
            'To_Vendor': baseline['vendor'],
            'To_System': baseline['family'],
            'To_DRE': baseline.get('is_dre', ''),
            'To_Marking_Method': baseline.get('marking_method', ''),
            'DRE_Status': 'No Change',
            'Marking_Method_Status': 'No Change',
            'Vendor_Retained': True,
            'Years_Between': years_between,
            'From_Baseline': True
        }
        no_turnover_rows.append(row)

    # Same fieldnames as between_system_turnovers.csv
    fieldnames = [
        'FIPS', 'State', 'Jurisdiction',
        'From_Year', 'From_Equipment', 'From_Vendor', 'From_System', 'From_DRE', 'From_Marking_Method',
        'To_Year', 'To_Equipment', 'To_Vendor', 'To_System', 'To_DRE', 'To_Marking_Method',
        'DRE_Status', 'Marking_Method_Status', 'Vendor_Retained', 'Years_Between', 'From_Baseline'
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(no_turnover_rows)

    return len(no_turnover_rows)


def print_summary_statistics(timelines, num_between, num_within, num_no_turnover):
    """Print summary statistics to console."""

    print()
    print("=" * 80)
    print("EQUIPMENT SYSTEM RENEWAL ANALYSIS (2006-2026)")
    print("=" * 80)
    print()

    # Basic counts
    total_jurisdictions = len(timelines)
    jurisdictions_with_changes = sum(1 for t in timelines.values() if len(t['timeline']) > 1)
    total_changes = num_between + num_within

    print(f"Total jurisdictions tracked: {total_jurisdictions:,}")
    print(f"Jurisdictions with changes: {jurisdictions_with_changes:,} ({jurisdictions_with_changes/total_jurisdictions*100:.1f}%)")
    jurisdictions_no_change = sum(1 for t in timelines.values() if len(t['timeline']) == 1)
    print(f"Jurisdictions with no changes: {jurisdictions_no_change:,} ({jurisdictions_no_change/total_jurisdictions*100:.1f}%)")
    print(f"  - Excluding Hand Count: {num_no_turnover:,}")
    print()
    print(f"Between-system turnovers: {num_between:,} ({num_between/total_changes*100:.1f}%)")
    print(f"Within-system turnovers: {num_within:,} ({num_within/total_changes*100:.1f}%)")
    print(f"Total turnover events: {total_changes:,}")
    print()

    # Vendor retention
    retention_stats = defaultdict(int)
    years_between = []
    upgrade_paths = Counter()

    for fips, data in timelines.items():
        timeline = data['timeline']

        for i in range(len(timeline) - 1):
            from_entry = timeline[i]
            to_entry = timeline[i + 1]

            # Retention
            if from_entry['vendor'] == to_entry['vendor']:
                retention_stats['retained'] += 1
            else:
                retention_stats['switched'] += 1

            # Years between changes
            years_between.append(to_entry['year'] - from_entry['year'])

            # Upgrade paths
            path = f"{from_entry['equipment']} → {to_entry['equipment']}"
            upgrade_paths[path] += 1

    if total_changes > 0:
        print("Vendor Retention:")
        print(f"  - Retained same vendor: {retention_stats['retained']:,} ({retention_stats['retained']/total_changes*100:.1f}%)")
        print(f"  - Switched vendor: {retention_stats['switched']:,} ({retention_stats['switched']/total_changes*100:.1f}%)")
        print()

        avg_years = sum(years_between) / len(years_between)
        print(f"Average years between changes: {avg_years:.1f} years")
        print()

        print("Top Equipment Upgrades:")
        for i, (path, count) in enumerate(upgrade_paths.most_common(10), 1):
            print(f"  {i}. {path}: {count:,} changes")
        print()

    print("=" * 80)


def main():
    """Main processing pipeline."""

    print("Loading data for all years...")
    data_by_year = load_all_years()
    print(f"✓ Loaded data for {len(data_by_year)} years")

    if 2006 not in data_by_year:
        print("Error: 2006 data not found. Cannot establish baselines.")
        return 1

    print()
    print("Initializing baselines from 2006...")
    timelines = initialize_baselines(data_by_year[2006])
    print(f"✓ Initialized {len(timelines):,} jurisdictions")

    print()
    print("Detecting equipment changes (both between-system and within-system)...")
    detect_changes(timelines, data_by_year, YEARS)
    print("✓ Change detection complete")

    print()
    print("Generating CSV files...")
    between_output = './data/between_system_turnovers.csv'
    within_output = './data/within_system_turnovers.csv'
    num_between, num_within = generate_two_csv_files(timelines, between_output, within_output)
    print(f"✓ Written {num_between:,} between-system changes to {between_output}")
    print(f"✓ Written {num_within:,} within-system changes to {within_output}")
    print(f"  Total turnover events: {num_between + num_within:,}")

    print()
    print("Generating no-turnover CSV...")
    no_turnover_output = './data/no_system_turnovers.csv'
    num_no_turnover = generate_no_turnover_csv(timelines, no_turnover_output)
    print(f"✓ Written {num_no_turnover:,} no-turnover jurisdictions to {no_turnover_output}")
    print(f"  (Excluded Hand Count jurisdictions)")

    print_summary_statistics(timelines, num_between, num_within, num_no_turnover)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
