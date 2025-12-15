#!/usr/bin/env python3
"""
Analyze patterns in within-system equipment turnovers.

Categorizes within-system changes into common patterns:
1. Central Scan ↔ Precinct Scan (same system, different deployment)
2. AccuVote TS ↔ AccuVote TSX (DRE model variations)
3. From DRE (moving away from DRE machines)
4. Within ES&S DS200 Generation (equipment changes within this system family)
5. Within Dominion ImageCast (equipment changes within this system family)
6. Within ES&S Model 100 Generation (equipment changes within this system family)
7. Other within-system changes

Reads from: ../../data/within_system_turnovers.csv
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict
import sys

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from equipment_constants import PREFIX_CENTRAL_SCAN, PREFIX_PRECINCT_SCAN

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
# Navigate up to project root and into data directory
DATA_DIR = SCRIPT_DIR.parent.parent / 'data'


def analyze_within_system_patterns():
    """Categorize and analyze within-system turnover patterns."""

    input_file = DATA_DIR / 'within_system_turnovers.csv'

    # Pattern categories
    central_precinct_changes = []
    accuvote_ts_tsx_changes = []
    from_dre_changes = []
    ess_ds200_changes = []
    dominion_imagecast_changes = []
    ess_model100_changes = []
    other_changes = []

    # Detailed counters for other changes
    other_patterns = Counter()
    other_by_system = defaultdict(list)

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            from_equipment = row['From_Equipment']
            to_equipment = row['To_Equipment']
            system = row['From_System']
            dre_status = row['DRE_Status']

            # Check for Central ↔ Precinct Scan pattern
            if (PREFIX_CENTRAL_SCAN in from_equipment and PREFIX_PRECINCT_SCAN in to_equipment) or \
               (PREFIX_PRECINCT_SCAN in from_equipment and PREFIX_CENTRAL_SCAN in to_equipment):
                central_precinct_changes.append(row)

            # Check for AccuVote TS ↔ TSX pattern
            elif ('AccuVote TS' in from_equipment and 'AccuVote TSX' in to_equipment) or \
                 ('AccuVote TSX' in from_equipment and 'AccuVote TS' in to_equipment):
                accuvote_ts_tsx_changes.append(row)

            # Check for From DRE pattern (moving away from DRE)
            elif dre_status == 'From DRE':
                from_dre_changes.append(row)

            # Check for ES&S DS200 Generation within-system changes
            elif system == 'ES&S DS200 Generation':
                ess_ds200_changes.append(row)

            # Check for Dominion ImageCast within-system changes
            elif system == 'Dominion ImageCast':
                dominion_imagecast_changes.append(row)

            # Check for ES&S Model 100 Generation within-system changes
            elif system == 'ES&S Model 100 Generation':
                ess_model100_changes.append(row)

            # Everything else
            else:
                other_changes.append(row)
                pattern = f"{from_equipment} → {to_equipment}"
                other_patterns[pattern] += 1
                other_by_system[system].append(pattern)

    # Print summary report
    print()
    print("=" * 100)
    print("WITHIN-SYSTEM TURNOVER PATTERN ANALYSIS")
    print("=" * 100)
    print()

    total = len(central_precinct_changes) + len(accuvote_ts_tsx_changes) + len(from_dre_changes) + len(ess_ds200_changes) + len(dominion_imagecast_changes) + len(ess_model100_changes) + len(other_changes)

    print(f"Total within-system turnovers: {total:,}")
    print()

    # Central ↔ Precinct Scan
    print(f"1. CENTRAL SCAN ↔ PRECINCT SCAN: {len(central_precinct_changes):,} changes ({len(central_precinct_changes)/total*100:.1f}%)")
    print("   Jurisdictions changing scanning deployment model within same system")
    print()

    # Count direction
    precinct_to_central = sum(1 for r in central_precinct_changes if PREFIX_PRECINCT_SCAN in r['From_Equipment'])
    central_to_precinct = len(central_precinct_changes) - precinct_to_central

    print(f"   - Precinct Scan → Central Scan: {precinct_to_central:,}")
    print(f"   - Central Scan → Precinct Scan: {central_to_precinct:,}")
    print()

    # Show most common systems involved
    system_counter = Counter(r['From_System'] for r in central_precinct_changes)
    print("   Top systems involved:")
    for system, count in system_counter.most_common(5):
        print(f"     • {system}: {count:,} changes")
    print()

    # AccuVote TS ↔ TSX
    print(f"2. ACCUVOTE TS ↔ TSX: {len(accuvote_ts_tsx_changes):,} changes ({len(accuvote_ts_tsx_changes)/total*100:.1f}%)")
    print("   DRE model variations (TS vs TSX)")
    print()

    # Count direction
    ts_to_tsx = sum(1 for r in accuvote_ts_tsx_changes if 'AccuVote TS' in r['From_Equipment'] and 'TSX' in r['To_Equipment'])
    tsx_to_ts = len(accuvote_ts_tsx_changes) - ts_to_tsx

    print(f"   - AccuVote TS → AccuVote TSX: {ts_to_tsx:,}")
    print(f"   - AccuVote TSX → AccuVote TS: {tsx_to_ts:,}")
    print()

    # From DRE
    print(f"3. FROM DRE: {len(from_dre_changes):,} changes ({len(from_dre_changes)/total*100:.1f}%)")
    print("   Jurisdictions moving away from DRE machines within same system family")
    print()

    # Show most common patterns
    from_dre_patterns = Counter(f"{r['From_Equipment']} → {r['To_Equipment']}" for r in from_dre_changes)
    print("   Top patterns:")
    for i, (pattern, count) in enumerate(from_dre_patterns.most_common(10), 1):
        print(f"     {i:2d}. {pattern}: {count:,} changes")
    print()

    # Show systems involved
    from_dre_systems = Counter(r['From_System'] for r in from_dre_changes)
    print("   Systems involved:")
    for system, count in from_dre_systems.most_common():
        print(f"     • {system}: {count:,} changes")
    print()

    # ES&S DS200 Generation
    print(f"4. WITHIN ES&S DS200 GENERATION: {len(ess_ds200_changes):,} changes ({len(ess_ds200_changes)/total*100:.1f}%)")
    print("   Equipment changes within ES&S DS200 Generation system family")
    print()

    # Show most common patterns
    ess_ds200_patterns = Counter(f"{r['From_Equipment']} → {r['To_Equipment']}" for r in ess_ds200_changes)
    print("   Top patterns:")
    for i, (pattern, count) in enumerate(ess_ds200_patterns.most_common(10), 1):
        print(f"     {i:2d}. {pattern}: {count:,} changes")
    print()

    # Dominion ImageCast
    print(f"5. WITHIN DOMINION IMAGECAST: {len(dominion_imagecast_changes):,} changes ({len(dominion_imagecast_changes)/total*100:.1f}%)")
    print("   Equipment changes within Dominion ImageCast system family")
    print()

    # Show most common patterns
    dominion_imagecast_patterns = Counter(f"{r['From_Equipment']} → {r['To_Equipment']}" for r in dominion_imagecast_changes)
    print("   Top patterns:")
    for i, (pattern, count) in enumerate(dominion_imagecast_patterns.most_common(10), 1):
        print(f"     {i:2d}. {pattern}: {count:,} changes")
    print()

    # ES&S Model 100 Generation
    print(f"6. WITHIN ES&S MODEL 100 GENERATION: {len(ess_model100_changes):,} changes ({len(ess_model100_changes)/total*100:.1f}%)")
    print("   Equipment changes within ES&S Model 100 Generation system family")
    print()

    # Show most common patterns
    ess_model100_patterns = Counter(f"{r['From_Equipment']} → {r['To_Equipment']}" for r in ess_model100_changes)
    print("   Top patterns:")
    for i, (pattern, count) in enumerate(ess_model100_patterns.most_common(10), 1):
        print(f"     {i:2d}. {pattern}: {count:,} changes")
    print()

    # Other changes
    print(f"7. OTHER WITHIN-SYSTEM CHANGES: {len(other_changes):,} changes ({len(other_changes)/total*100:.1f}%)")
    print("   Various equipment upgrades/changes within same system family")
    print()

    print(f"   Total unique patterns: {len(other_patterns):,}")
    print()

    print("   Top 15 most common patterns:")
    for i, (pattern, count) in enumerate(other_patterns.most_common(15), 1):
        print(f"     {i:2d}. {pattern}: {count:,} changes")
    print()

    print("   Breakdown by system family:")
    system_counts = {system: len(patterns) for system, patterns in other_by_system.items()}
    for system, count in sorted(system_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"     • {system}: {count:,} changes")
    print()

    print("=" * 100)

    # Return statistics
    return {
        'total': total,
        'central_precinct': len(central_precinct_changes),
        'accuvote': len(accuvote_ts_tsx_changes),
        'from_dre': len(from_dre_changes),
        'ess_ds200': len(ess_ds200_changes),
        'dominion_imagecast': len(dominion_imagecast_changes),
        'ess_model100': len(ess_model100_changes),
        'other': len(other_changes)
    }


if __name__ == '__main__':
    stats = analyze_within_system_patterns()
    print()
    print(f"✓ Analysis complete")
    print(f"  {stats['central_precinct']:,} Central↔Precinct, {stats['accuvote']:,} AccuVote TS↔TSX, {stats['from_dre']:,} From DRE, {stats['ess_ds200']:,} ES&S DS200 Gen, {stats['dominion_imagecast']:,} Dominion ImageCast, {stats['ess_model100']:,} ES&S Model 100 Gen, {stats['other']:,} Other")
