# Voting Equipment and Poll Book Analysis

Analysis of U.S. voting equipment deployment, turnover patterns, vendor switching behavior, and poll book adoption across jurisdictions from 2006-2026.

## Data Source

**Primary Data**: Verified Voting - Equipment Verifier Data

Verified Voting tracks all equipment for marking or tabulating ballots across all U.S. election jurisdictions. Raw verifier data shows which types of voting equipment were used for each jurisdiction for each two year election cycle.

**Supplementary Data**:
- **HAVA Funding**: EAC HAVA funding levels by state and year (2002-Present)

## Data Time Range

**Verifier Data**: Even years 2006 to 2026. 2026 data may still change. Where available, "First Year In Use" metadata extends equipment deployment history back to 1952 (lever machines!) but only for a handful of jurisdictions.

**HAVA Funding Data**: Complete data, 2003 to present.

## Methods: Condensing Verified Voting Data

### Problem
Raw EAC verifier data contains **multiple rows per jurisdiction** (one per piece of equipment). This data is noisy in a couple of ways:
- There are multiple vendors at each point in time. In addition to the voting system vendor, there may be the poll book vendor, separate accessible voting machine vendor, remote ballot marking vendor, and so on.
- Two jurisdictions might be using the same DRE, but for one, it is just for accessible voting, and for the other, it is the main system.
- There may be model changes within the same family, e.g. jurisdiction gets a DS850 to use alongside an existing DS450
- The county may change their deployment model within the same system, e.g. primarily precinct scan to primarily central scan, but all ImageCast

To analyze jurisdictions as part of a clean time series, we must identify each jurisdiction's **primary voting system**.

### Identifying Primary Voting Equipment

When looking at a jurisdiction's data and list of equipment, the decision tree is roughly as follows:

1. Handle "machine voting for all" jurisdictions
  a. If tagged as "BMD for all" - BMD is the primary equipment
  b. If tagged as "DRE for all" - DRE is the primary equipment
  c. If tagged as "Mechanical Lever Machine" - lever machine is the primary equipment
  d. If tagged as a punch card system - punch card system is the primary equipment
2. If tagged as an all mail jurisdiction
  a. If has batch scanners - the batch scanner is the primary, central scan equipment (but treat all DS450, DS850, DS950 the same)
  b. If only has hand-fed scanners - the hand-fed scanner is the primary, central scan equipment
  c. Hand Count
3. If has hand-fed scanners - the hand-fed scanner is the primary, precinct scan equipment
4. If has central scanners (but is not all mail) - the central scanners are the primary, central scan equipment
5. If has "Hand Count" in the data or is smaller than 500 registered voters - the primary equipment is hand count
6. Tag anything that gets here as an "Anomaly"

If there are two pieces of equipment for a category (e.g. two BMDs, two batch scanners), use the earliest one.

### Identifying Primary Voting System

Roll up the primary voting equipment field into a primary voting system field. For example, AccuVote OS and AccuVote OSX are basically the same. Dominion ImageCast precinct scan and central scan are basically the same, with a shift in emphasis.

### Identifying Primary Vendor

Vendor name is usually in the equipment name. Extract it based on a list of expected values and shunt others to "Other." Companies that are eventually acquired (e.g. Sequoia) are grouped under their eventual vendor.

### Poll Book Classification

Poll books are classified as:
- **Paper**: Traditional paper poll books
- **Commercial Electronic**: Manufacturer-branded e-poll books (KNOWiNK, Tenex, Robis, etc.)
- **In-House**: Custom/in-house electronic poll book systems

Priority logic: Paper > In-House > Commercial (if multiple types present, the highest priority wins)

### Output

For each year, condensing produces:
- **`{YEAR}_verifier-jurisdictions-condensed.csv`**: One row per jurisdiction with primary voting system fields
- **`{YEAR}_summary_report.md`**: Statistical summary of equipment distribution for the year

## Methods: Identifying Turnover

The turnover analysis (`identify_voting_equipment_turnover.py`) tracks changes across consecutive election cycles (2006→2008, 2008→2010, etc.), with three types of turnover.

### 1. Between-System Turnovers
**Definition**: Jurisdictions that changed their **primary voting system** (vendor switch or major system upgrade).

**Examples**:
- ES&S DS200 → Dominion ImageCast (vendor switch)
- AccuVote TS (DRE) → ES&S DS200 (optical scan)
- Hart eSeries → Hart Verity (same vendor, different generation)

**Output**: `data/between_system_turnovers.csv`

**Key Fields**:
- `From_Equipment`, `To_Equipment`: Full equipment names
- `From_Vendor`, `To_Vendor`: Vendor names
- `From_Family`, `To_Family`: Equipment family classifications
- `Vendor_Retained`: Boolean indicating if vendor stayed the same
- `Years_Between`: Time elapsed between changes

### 2. Within-System Turnovers
**Definition**: Jurisdictions that changed **equipment model** within the **same family**

**Examples**:
- Precinct vs. Central Scan Switches, e.g. "Precinct Scan - Dominion ImageCast" → "Central Scan - Dominion ImageCast", 40% of changes
- AccuVote TS Switches, e.g. AccuVote TS → AccuVote TSX, 33% of changes
- Away from DRE, e.g. "DRE - Hart InterCivic Verity Touch" → "BMD - Hart InterCivic Verity Duo", 8% of changes

**Output**: `data/within_system_turnovers.csv`

**Note**: These represent incremental upgrades or replacements within an existing vendor relationship.

### 3. No-Turnover Jurisdictions
**Definition**: Jurisdictions that used the **same equipment** across the entire 2006-2026 period

**Output**: `data/no_system_turnovers.csv`

**Note**: These jurisdictions represent equipment that has been in service for 20+ years without replacement.

## Key Equipment Analysis Outputs

### Equipment Lifecycle Analysis (`equipment_analysis/`)
- **`lifecycle_distribution_all.png`**: Distribution of equipment lifecycle lengths (all turnovers)
- **`lifecycle_distribution_from_paper.png`**: Lifecycle for HMPB (hand-marked paper ballot) systems
- **`lifecycle_distribution_from_bmd.png`**: Lifecycle for BMD systems
- **`lifecycle_distribution_from_dre.png`**: Lifecycle for DRE systems

### Vendor Turnover Analysis (`equipment_analysis/`)
- **`turnover_volume_by_year.png`**: Total number of turnovers per year
- **`turnover_percentage_jurisdictions.png`**: Turnover as % of all jurisdictions
- **`turnover_percentage_voters.png`**: Turnover as % of registered voters
- **`turnover_and_hava_funding.png`**: Dual-axis chart comparing turnover % with HAVA funding levels
- **`vendor_switching_matrix.png`**: Heatmap showing vendor retention and switching patterns
- **`vendor_retention_timeline.png`**: Vendor retention rates over time (2006-2026)

### Jurisdiction Trends (`data_quality_tools/jurisdiction_trends/`)
- **Marking Method Trends**: Evolution of hand-marked vs machine-marked voting over time
- **Tabulation Trends**: Precinct vs central tabulation patterns
- **All-Mail Ballot Trends**: Adoption of all-mail voting
- **Voting Location Trends**: Vote center vs precinct-based voting

Applicable trends are visualized in two ways:
1. **By jurisdiction count**: Each jurisdiction counted equally
2. **Weighted by registered voters**: Larger jurisdictions weighted more heavily

## Data Quality Tools

The `data_quality_tools/` directory contains scripts for exploring and validating the data:

### `/jurisdiction_condensed_values/`
Tools for analyzing field values in condensed jurisdiction data:
- **`report_unique_condensed_values.py`**: Lists all unique values for each condensed field
- **`report_anomaly_details.py`**: Identifies and reports data anomalies across years

### `/jurisdiction_trends/`
Visualization tools for tracking field values over time:
- **`analyze_jurisdiction_trends.py`**: Generates stacked bar charts showing how marking methods, tabulation, and voting locations change over time

### `/machines/`
Machine-level data analysis:
- **`find_duplicate_equipment.py`**: Identifies duplicate equipment records

### `/turnover/`
Turnover pattern investigation:
- **`inspect_no_turnover.py`**: Analyzes jurisdictions with no equipment changes
- **`inspect_quick_turnover.py`**: Identifies unusually short equipment lifecycles
- **`analyze_within_system_patterns.py`**: Studies patterns in same-family equipment changes

**Usage**: Run any script to generate detailed reports and identify data quality issues or interesting patterns.

## Usage

To generate all data, analysis, and images:

```bash
# With Verified Voting zip archives in the ./data/downloads directory
python3 run_all.py
``` 

## Known Data Issues
- Oregon is not "All Mail" for a year
- Georgia toggled between TSX and TS and back

Inconsistent Machine Identification
- Diebold appears as both "Diebold" and "Premier (Diebold)"
- "InkaVote Plus" and "InkaVote Plus PBC" both appear
- Plain "ImageCast" appears as a BMD
- "OpenElect OVI" and "OpenElection OVI-VC" both appear
- "AccuVote OS Central" and "Premier Central Scan" both appear
- "DS200" labelled as a batch scanner in a couple places. Same for Model 115 and Model 315?
- 
