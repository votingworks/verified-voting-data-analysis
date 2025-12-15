#!/usr/bin/env python3
"""
Inspect jurisdictions with quick equipment turnover (≤2 years).

Identifies jurisdictions that changed equipment with 2 years or less between changes,
which may indicate failed deployments, pilot programs, or other anomalies.
Includes vendor switches.
"""

import csv
from collections import defaultdict


def load_renewals():
    """Load equipment family changes data."""
    renewals = []

    with open('../../data/between_system_turnover.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            renewals.append(row)

    return renewals


def find_quick_turnover(renewals, max_years=4, filter_normal=False):
    """
    Find all renewal events with quick turnover (≤ max_years).

    Args:
        max_years: Maximum years between changes to include
        filter_normal: If True, exclude normal upgrade paths (vendor switches,
                      Hand Count transitions, and known normal cross-family upgrades)

    Returns:
        dict: {fips: [list of quick turnover events]}
    """
    quick_turnover = defaultdict(list)

    for renewal in renewals:
        years_between = int(renewal['Years_Between'])

        if years_between <= max_years:
            # Apply filters if enabled
            if filter_normal:
                from_eq = renewal['From_Equipment']
                to_eq = renewal['To_Equipment']
                vendor_retained = renewal['Vendor_Retained']

                # NOTE: Vendor switches are now INCLUDED (not filtered out)
                # This allows us to see rapid vendor changes which may indicate issues

                # Filter out Hand Count (not equipment upgrades)
                if from_eq == 'Hand Count':
                    continue

                # Note: No need to filter Family_Changed anymore!
                # The renewals data now only includes family changes by design.
                # All within-family upgrades (DS200→ExpressVote, eScan→eSlate, etc.)
                # are already filtered out upstream in the renewals calculation.

                # Exceptions: Known normal cross-family upgrades/migrations
                # Even though these are cross-family, they're standard product transitions

                # ES&S normal product line upgrades
                if from_eq == 'ES&S Model 100' and to_eq == 'ES&S DS200':
                    continue  # DS200 was the designated replacement for Model 100
                if from_eq == 'ES&S DS200' and to_eq == 'ES&S DS300':
                    continue  # DS300 is the high-speed successor to DS200

                # Dominion migrations from Optech/Sequoia to ImageCast
                if 'Optech' in from_eq and 'ImageCast' in to_eq:
                    continue  # Standard migration path after Dominion acquired Sequoia

                # AccuVote TSX → OS (DRE to optical scan migration)
                if from_eq == 'AccuVote TSX' and to_eq == 'AccuVote OS':
                    continue  # Common migration after DRE concerns

            fips = renewal['FIPS']
            quick_turnover[fips].append(renewal)

    return quick_turnover


def write_quick_turnover_report(quick_turnover, output_file):
    """Write quick turnover report to file."""

    # Sort by state, then jurisdiction
    sorted_jurisdictions = sorted(
        quick_turnover.items(),
        key=lambda x: (x[1][0]['State'], x[1][0]['Jurisdiction'])
    )

    # Count total events
    total_events = sum(len(events) for events in quick_turnover.values())

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('ANOMALOUS FAMILY QUICK EQUIPMENT TURNOVER (≤2 YEARS)\n')
        f.write('INCLUDING: Vendor switches\n')
        f.write('EXCLUDING: Hand Count and known normal family upgrades\n')
        f.write('=' * 100 + '\n\n')
        f.write(f'Total jurisdictions with anomalous quick turnover: {len(quick_turnover):,}\n')
        f.write(f'Total anomalous quick turnover events: {total_events:,}\n\n')
        f.write('=' * 100 + '\n\n')

        current_state = None

        for fips, events in sorted_jurisdictions:
            state = events[0]['State']
            jurisdiction = events[0]['Jurisdiction']

            # State header
            if state != current_state:
                if current_state is not None:
                    f.write('\n')
                f.write(f'\n{state}\n')
                f.write('-' * 100 + '\n')
                current_state = state

            # Jurisdiction header
            f.write(f'\n{jurisdiction} (FIPS: {fips})\n')
            f.write(f'  {len(events)} quick turnover event(s):\n\n')

            # List each quick turnover event
            for event in events:
                from_year = event['From_Year']
                to_year = event['To_Year']
                years = event['Years_Between']
                from_eq = event['From_Equipment']
                to_eq = event['To_Equipment']
                from_vendor = event['From_Vendor']
                to_vendor = event['To_Vendor']
                from_family = event.get('From_Family', '')
                to_family = event.get('To_Family', '')
                vendor_retained = event['Vendor_Retained']
                from_baseline = event['From_Baseline']

                f.write(f'  • {from_year} → {to_year} ({years} years)\n')
                f.write(f'    From: {from_eq} ({from_vendor})\n')
                if from_family and from_family != from_eq:
                    f.write(f'          Family: {from_family}\n')
                f.write(f'    To:   {to_eq} ({to_vendor})\n')
                if to_family and to_family != to_eq:
                    f.write(f'          Family: {to_family}\n')

                if vendor_retained == 'True':
                    f.write(f'    Vendor: RETAINED ({from_vendor})\n')
                else:
                    f.write(f'    Vendor: SWITCHED ({from_vendor} → {to_vendor})\n')

                if from_baseline == 'True':
                    f.write(f'    Note: From year is baseline (first observed)\n')

                f.write('\n')

        # Summary statistics
        f.write('\n')
        f.write('=' * 100 + '\n')
        f.write('SUMMARY STATISTICS\n')
        f.write('=' * 100 + '\n\n')

        # Years distribution
        years_dist = defaultdict(int)
        vendor_switched = 0
        vendor_retained = 0
        from_baseline_count = 0

        for events in quick_turnover.values():
            for event in events:
                years_dist[int(event['Years_Between'])] += 1
                if event['Vendor_Retained'] == 'True':
                    vendor_retained += 1
                else:
                    vendor_switched += 1
                if event['From_Baseline'] == 'True':
                    from_baseline_count += 1

        f.write('Years Between Changes:\n')
        for years in sorted(years_dist.keys()):
            count = years_dist[years]
            pct = count / total_events * 100
            f.write(f'  {years} years: {count:,} events ({pct:.1f}%)\n')

        f.write('\n')
        f.write('Vendor Retention:\n')
        f.write(f'  Retained: {vendor_retained:,} events ({vendor_retained/total_events*100:.1f}%)\n')
        f.write(f'  Switched: {vendor_switched:,} events ({vendor_switched/total_events*100:.1f}%)\n')

        f.write('\n')
        f.write(f'From Baseline: {from_baseline_count:,} events ({from_baseline_count/total_events*100:.1f}%)\n')

        # Equipment upgrade paths
        f.write('\n')
        f.write('Most Common Quick Turnover Paths:\n')

        upgrade_paths = defaultdict(int)
        for events in quick_turnover.values():
            for event in events:
                path = f"{event['From_Equipment']} → {event['To_Equipment']}"
                upgrade_paths[path] += 1

        for i, (path, count) in enumerate(sorted(upgrade_paths.items(), key=lambda x: -x[1])[:15], 1):
            f.write(f'  {i}. {path}: {count:,}\n')


def main():
    print("Loading equipment family changes data...")
    renewals = load_renewals()
    print(f"✓ Loaded {len(renewals):,} family change events")

    print("\nFinding anomalous family quick turnover events (≤2 years)...")
    print("  Including: Vendor switches")
    print("  Excluding: Hand Count and known normal upgrades")
    quick_turnover = find_quick_turnover(renewals, max_years=2, filter_normal=True)

    total_events = sum(len(events) for events in quick_turnover.values())
    print(f"✓ Found {len(quick_turnover):,} jurisdictions with {total_events:,} anomalous quick turnover events")

    output_file = 'quick_turnover_jurisdictions_anomalies.txt'
    print(f"\nWriting report to {output_file}...")
    write_quick_turnover_report(quick_turnover, output_file)
    print(f"✓ Report written to {output_file}")

    print(f"\n{len(quick_turnover):,} jurisdictions had anomalous equipment changes ≤2 years apart")


if __name__ == "__main__":
    main()
