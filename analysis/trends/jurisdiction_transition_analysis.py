#!/usr/bin/env python3
"""
Analyze jurisdiction transitions from jurisdiction_transitions.csv.

Generates a text report showing:
- Summary of transition types and quantities
- For each type, breakdown of specific transitions and frequencies

Output: outputs/reports/jurisdiction_transition_analysis.txt
"""

import csv
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
INPUT_PATH = PROJECT_ROOT / 'data' / 'processed' / 'jurisdiction_transitions.csv'
OUTPUT_PATH = PROJECT_ROOT / 'outputs' / 'reports' / 'jurisdiction_transition_analysis.txt'


def load_transitions():
    """Load jurisdiction_transitions.csv, excluding baselines."""
    print("Loading jurisdiction_transitions.csv...")
    transitions = []
    baselines = []

    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Transition_Type'] == 'baseline':
                baselines.append(row)
            else:
                transitions.append(row)

    print(f"  Loaded {len(transitions):,} transitions and {len(baselines):,} baselines")
    return transitions, baselines


def analyze_vendor_transitions(transitions):
    """Analyze vendor transition patterns."""
    vendor_transitions = [t for t in transitions if t['Transition_Type'] == 'vendor']

    # Count From -> To vendor pairs
    vendor_pairs = Counter()
    for t in vendor_transitions:
        pair = f"{t['From_Primary_Voting_Vendor']} -> {t['To_Primary_Voting_Vendor']}"
        vendor_pairs[pair] += 1

    # Count by destination vendor
    to_vendor = Counter(t['To_Primary_Voting_Vendor'] for t in vendor_transitions)

    # Count by source vendor
    from_vendor = Counter(t['From_Primary_Voting_Vendor'] for t in vendor_transitions)

    return {
        'total': len(vendor_transitions),
        'pairs': vendor_pairs,
        'to_vendor': to_vendor,
        'from_vendor': from_vendor,
    }


def analyze_system_transitions(transitions):
    """Analyze system transition patterns."""
    system_transitions = [t for t in transitions if t['Transition_Type'] == 'system']

    # Count From -> To system pairs
    system_pairs = Counter()
    for t in system_transitions:
        pair = f"{t['From_Primary_Voting_System']} -> {t['To_Primary_Voting_System']}"
        system_pairs[pair] += 1

    # Count by destination system
    to_system = Counter(t['To_Primary_Voting_System'] for t in system_transitions)

    # Count by source system
    from_system = Counter(t['From_Primary_Voting_System'] for t in system_transitions)

    return {
        'total': len(system_transitions),
        'pairs': system_pairs,
        'to_system': to_system,
        'from_system': from_system,
    }


def analyze_mail_transitions(transitions):
    """Analyze mail transition patterns."""
    mail_transitions = [t for t in transitions if t['Transition_Type'] == 'mail']

    # Count direction
    to_mail = sum(1 for t in mail_transitions
                  if t['From_All_Mail_Ballot'] == 'No' and t['To_All_Mail_Ballot'] == 'Yes')
    from_mail = sum(1 for t in mail_transitions
                    if t['From_All_Mail_Ballot'] == 'Yes' and t['To_All_Mail_Ballot'] == 'No')

    # Group by state
    by_state = defaultdict(lambda: {'to_mail': 0, 'from_mail': 0})
    for t in mail_transitions:
        if t['From_All_Mail_Ballot'] == 'No' and t['To_All_Mail_Ballot'] == 'Yes':
            by_state[t['State']]['to_mail'] += 1
        else:
            by_state[t['State']]['from_mail'] += 1

    # Group by year
    by_year = defaultdict(lambda: {'to_mail': 0, 'from_mail': 0})
    for t in mail_transitions:
        year = t['To_Year']
        if t['From_All_Mail_Ballot'] == 'No' and t['To_All_Mail_Ballot'] == 'Yes':
            by_year[year]['to_mail'] += 1
        else:
            by_year[year]['from_mail'] += 1

    return {
        'total': len(mail_transitions),
        'to_mail': to_mail,
        'from_mail': from_mail,
        'by_state': dict(by_state),
        'by_year': dict(by_year),
    }


def analyze_equipment_transitions(transitions):
    """Analyze equipment transition patterns."""
    equipment_transitions = [t for t in transitions if t['Transition_Type'] == 'equipment']

    # Count From -> To equipment pairs
    equipment_pairs = Counter()
    for t in equipment_transitions:
        pair = f"{t['From_Primary_Voting_Equipment']} -> {t['To_Primary_Voting_Equipment']}"
        equipment_pairs[pair] += 1

    # Count by destination equipment
    to_equipment = Counter(t['To_Primary_Voting_Equipment'] for t in equipment_transitions)

    return {
        'total': len(equipment_transitions),
        'pairs': equipment_pairs,
        'to_equipment': to_equipment,
    }


def analyze_vvpat_transitions(transitions):
    """Analyze VVPAT upgrade and downgrade patterns."""
    upgrades = [t for t in transitions if t['Transition_Type'] == 'vvpat_upgrade']
    downgrades = [t for t in transitions if t['Transition_Type'] == 'vvpat_downgrade']

    # Upgrades by state/year/vendor
    upgrade_by_state = Counter(t['State'] for t in upgrades)
    upgrade_by_year = Counter(t['To_Year'] for t in upgrades)
    upgrade_by_vendor = Counter(t['To_Primary_Voting_Vendor'] for t in upgrades)

    # Downgrades by state/year
    downgrade_by_state = Counter(t['State'] for t in downgrades)
    downgrade_by_year = Counter(t['To_Year'] for t in downgrades)

    return {
        'upgrades': len(upgrades),
        'downgrades': len(downgrades),
        'upgrade_by_state': upgrade_by_state,
        'upgrade_by_year': upgrade_by_year,
        'upgrade_by_vendor': upgrade_by_vendor,
        'downgrade_by_state': downgrade_by_state,
        'downgrade_by_year': downgrade_by_year,
        'downgrade_examples': downgrades[:5],  # First 5 examples for debugging
    }


def analyze_hand_count_transitions(transitions):
    """Analyze hand count transition patterns."""
    to_hand_count = [t for t in transitions if t['Transition_Type'] == 'to_hand_count']
    from_hand_count = [t for t in transitions if t['Transition_Type'] == 'from_hand_count']

    # To hand count by state/year
    to_by_state = Counter(t['State'] for t in to_hand_count)
    to_by_year = Counter(t['To_Year'] for t in to_hand_count)
    to_from_class = Counter(t['From_Voting_Class'] for t in to_hand_count)

    # From hand count by state/year
    from_by_state = Counter(t['State'] for t in from_hand_count)
    from_by_year = Counter(t['To_Year'] for t in from_hand_count)
    from_to_class = Counter(t['To_Voting_Class'] for t in from_hand_count)

    return {
        'to_hand_count': len(to_hand_count),
        'from_hand_count': len(from_hand_count),
        'to_by_state': to_by_state,
        'to_by_year': to_by_year,
        'to_from_class': to_from_class,
        'from_by_state': from_by_state,
        'from_by_year': from_by_year,
        'from_to_class': from_to_class,
    }


def analyze_other_transitions(transitions):
    """Analyze 'other' transitions for debugging."""
    other_transitions = [t for t in transitions if t['Transition_Type'] == 'other']

    # Categorize what changed
    categories = defaultdict(list)
    for t in other_transitions:
        changes = []
        if t['From_Voting_Class'] != t['To_Voting_Class']:
            changes.append(f"Voting_Class: {t['From_Voting_Class']} -> {t['To_Voting_Class']}")
        if t['From_Primary_Marking_Method'] != t['To_Primary_Marking_Method']:
            changes.append(f"Marking_Method: {t['From_Primary_Marking_Method']} -> {t['To_Primary_Marking_Method']}")

        category = "; ".join(changes) if changes else "Unknown"
        categories[category].append(t)

    return {
        'total': len(other_transitions),
        'categories': {k: len(v) for k, v in categories.items()},
        'examples': {k: v[:3] for k, v in categories.items()},  # First 3 examples per category
    }


def write_report(transitions, baselines, output_path):
    """Write the analysis report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("JURISDICTION TRANSITION ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        # Overall summary
        f.write("SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"Total baselines: {len(baselines):,}\n")
        f.write(f"Total transitions: {len(transitions):,}\n\n")

        # Count by type
        type_counts = Counter(t['Transition_Type'] for t in transitions)
        f.write("Transitions by type:\n")
        priority_order = ['vendor', 'system', 'mail', 'equipment', 'vvpat_upgrade',
                          'vvpat_downgrade', 'to_hand_count', 'from_hand_count', 'other']
        for t_type in priority_order:
            count = type_counts.get(t_type, 0)
            pct = count / len(transitions) * 100 if transitions else 0
            f.write(f"  {t_type}: {count:,} ({pct:.1f}%)\n")
        f.write("\n")

        # =====================================================================
        # VENDOR TRANSITIONS
        # =====================================================================
        f.write("\n" + "=" * 80 + "\n")
        f.write("VENDOR TRANSITIONS\n")
        f.write("=" * 80 + "\n\n")

        vendor_data = analyze_vendor_transitions(transitions)
        f.write(f"Total vendor switches: {vendor_data['total']:,}\n\n")

        f.write("Vendors gained market share (destination vendor):\n")
        for vendor, count in vendor_data['to_vendor'].most_common():
            f.write(f"  {vendor}: {count:,}\n")

        f.write("\nVendors lost market share (source vendor):\n")
        for vendor, count in vendor_data['from_vendor'].most_common():
            f.write(f"  {vendor}: {count:,}\n")

        f.write("\nTop vendor transition paths:\n")
        for pair, count in vendor_data['pairs'].most_common(20):
            f.write(f"  {pair}: {count:,}\n")

        # =====================================================================
        # SYSTEM TRANSITIONS
        # =====================================================================
        f.write("\n" + "=" * 80 + "\n")
        f.write("SYSTEM TRANSITIONS (same vendor)\n")
        f.write("=" * 80 + "\n\n")

        system_data = analyze_system_transitions(transitions)
        f.write(f"Total system upgrades: {system_data['total']:,}\n\n")

        f.write("Systems adopted (destination):\n")
        for system, count in system_data['to_system'].most_common(15):
            f.write(f"  {system}: {count:,}\n")

        f.write("\nSystems retired (source):\n")
        for system, count in system_data['from_system'].most_common(15):
            f.write(f"  {system}: {count:,}\n")

        f.write("\nTop system transition paths:\n")
        for pair, count in system_data['pairs'].most_common(25):
            f.write(f"  {pair}: {count:,}\n")

        # =====================================================================
        # MAIL TRANSITIONS
        # =====================================================================
        f.write("\n" + "=" * 80 + "\n")
        f.write("MAIL TRANSITIONS\n")
        f.write("=" * 80 + "\n\n")

        mail_data = analyze_mail_transitions(transitions)
        f.write(f"Total mail transitions: {mail_data['total']:,}\n")
        f.write(f"  Became all-mail (No -> Yes): {mail_data['to_mail']:,}\n")
        f.write(f"  Left all-mail (Yes -> No): {mail_data['from_mail']:,}\n\n")

        f.write("By year:\n")
        for year in sorted(mail_data['by_year'].keys()):
            data = mail_data['by_year'][year]
            f.write(f"  {year}: +{data['to_mail']} to mail, -{data['from_mail']} from mail\n")

        f.write("\nBy state:\n")
        for state in sorted(mail_data['by_state'].keys()):
            data = mail_data['by_state'][state]
            parts = []
            if data['to_mail'] > 0:
                parts.append(f"+{data['to_mail']} to mail")
            if data['from_mail'] > 0:
                parts.append(f"-{data['from_mail']} from mail")
            f.write(f"  {state}: {', '.join(parts)}\n")

        # =====================================================================
        # EQUIPMENT TRANSITIONS
        # =====================================================================
        f.write("\n" + "=" * 80 + "\n")
        f.write("EQUIPMENT TRANSITIONS (same system)\n")
        f.write("=" * 80 + "\n\n")

        equipment_data = analyze_equipment_transitions(transitions)
        f.write(f"Total equipment changes: {equipment_data['total']:,}\n\n")

        f.write("Equipment adopted:\n")
        for equipment, count in equipment_data['to_equipment'].most_common(15):
            f.write(f"  {equipment}: {count:,}\n")

        f.write("\nEquipment transition paths:\n")
        for pair, count in equipment_data['pairs'].most_common(20):
            f.write(f"  {pair}: {count:,}\n")

        # =====================================================================
        # VVPAT TRANSITIONS
        # =====================================================================
        f.write("\n" + "=" * 80 + "\n")
        f.write("VVPAT TRANSITIONS\n")
        f.write("=" * 80 + "\n\n")

        vvpat_data = analyze_vvpat_transitions(transitions)
        f.write(f"VVPAT upgrades (DRE without VVPAT -> with VVPAT): {vvpat_data['upgrades']:,}\n")
        f.write(f"VVPAT downgrades (DRE with VVPAT -> without VVPAT): {vvpat_data['downgrades']:,}\n\n")

        f.write("--- UPGRADES ---\n\n")
        f.write("By year:\n")
        for year, count in sorted(vvpat_data['upgrade_by_year'].items()):
            f.write(f"  {year}: {count:,}\n")

        f.write("\nBy state:\n")
        for state, count in vvpat_data['upgrade_by_state'].most_common():
            f.write(f"  {state}: {count:,}\n")

        f.write("\nBy vendor:\n")
        for vendor, count in vvpat_data['upgrade_by_vendor'].most_common():
            f.write(f"  {vendor}: {count:,}\n")

        f.write("\n--- DOWNGRADES (potential data quality issue) ---\n\n")
        f.write("By year:\n")
        for year, count in sorted(vvpat_data['downgrade_by_year'].items()):
            f.write(f"  {year}: {count:,}\n")

        f.write("\nBy state:\n")
        for state, count in vvpat_data['downgrade_by_state'].most_common():
            f.write(f"  {state}: {count:,}\n")

        if vvpat_data['downgrade_examples']:
            f.write("\nExample downgrades:\n")
            for ex in vvpat_data['downgrade_examples']:
                f.write(f"  - {ex['State']}, {ex['Jurisdiction']}: {ex['From_Year']} -> {ex['To_Year']}\n")
                f.write(f"    Equipment: {ex['From_Primary_Voting_Equipment']}\n")

        # =====================================================================
        # HAND COUNT TRANSITIONS
        # =====================================================================
        f.write("\n" + "=" * 80 + "\n")
        f.write("HAND COUNT TRANSITIONS\n")
        f.write("=" * 80 + "\n\n")

        hand_count_data = analyze_hand_count_transitions(transitions)
        f.write(f"Transitions TO hand count: {hand_count_data['to_hand_count']:,}\n")
        f.write(f"Transitions FROM hand count: {hand_count_data['from_hand_count']:,}\n\n")

        f.write("--- TO HAND COUNT ---\n\n")
        f.write("By year:\n")
        for year, count in sorted(hand_count_data['to_by_year'].items()):
            f.write(f"  {year}: {count:,}\n")

        f.write("\nBy state:\n")
        for state, count in hand_count_data['to_by_state'].most_common():
            f.write(f"  {state}: {count:,}\n")

        f.write("\nFrom which class:\n")
        for cls, count in hand_count_data['to_from_class'].most_common():
            f.write(f"  {cls}: {count:,}\n")

        f.write("\n--- FROM HAND COUNT ---\n\n")
        f.write("By year:\n")
        for year, count in sorted(hand_count_data['from_by_year'].items()):
            f.write(f"  {year}: {count:,}\n")

        f.write("\nBy state:\n")
        for state, count in hand_count_data['from_by_state'].most_common():
            f.write(f"  {state}: {count:,}\n")

        f.write("\nTo which class:\n")
        for cls, count in hand_count_data['from_to_class'].most_common():
            f.write(f"  {cls}: {count:,}\n")

        # =====================================================================
        # OTHER TRANSITIONS (DEBUG)
        # =====================================================================
        f.write("\n" + "=" * 80 + "\n")
        f.write("OTHER TRANSITIONS (DEBUG)\n")
        f.write("=" * 80 + "\n\n")

        other_data = analyze_other_transitions(transitions)
        f.write(f"Total 'other' transitions: {other_data['total']:,}\n\n")

        f.write("Categories of changes:\n")
        for category, count in sorted(other_data['categories'].items(), key=lambda x: -x[1]):
            f.write(f"\n  [{count:,}] {category}\n")

            # Show examples
            examples = other_data['examples'].get(category, [])
            for ex in examples:
                f.write(f"      - {ex['State']}, {ex['Jurisdiction']}: {ex['From_Year']} -> {ex['To_Year']}\n")
                f.write(f"        From: Class={ex['From_Voting_Class']}, Marking={ex['From_Primary_Marking_Method']}\n")
                f.write(f"        To:   Class={ex['To_Voting_Class']}, Marking={ex['To_Primary_Marking_Method']}\n")
                f.write(f"        Equipment: {ex['From_Primary_Voting_Equipment']} -> {ex['To_Primary_Voting_Equipment']}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")


def main():
    """Main processing pipeline."""
    print("=" * 60)
    print("JURISDICTION TRANSITION ANALYSIS")
    print("=" * 60)
    print()

    # Load data
    transitions, baselines = load_transitions()

    # Write report
    print(f"\nWriting report to {OUTPUT_PATH}...")
    write_report(transitions, baselines, OUTPUT_PATH)
    print("Done!")

    # Also print summary to console
    print("\n" + "-" * 60)
    print("SUMMARY")
    print("-" * 60)
    type_counts = Counter(t['Transition_Type'] for t in transitions)
    for t_type in ['vendor', 'system', 'mail', 'equipment', 'vvpat_upgrade',
                   'vvpat_downgrade', 'to_hand_count', 'from_hand_count', 'other']:
        count = type_counts.get(t_type, 0)
        print(f"  {t_type}: {count:,}")
    print(f"\nFull report: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
