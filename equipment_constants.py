"""
Shared constants for voting equipment classification across all analysis scripts.

This module provides consistent equipment type prefixes and classifications
used throughout the codebase for categorizing and analyzing voting equipment.
"""

# ============================================================================
# EQUIPMENT PREFIX CONSTANTS
# ============================================================================

PREFIX_MACHINE = "Machine - "
PREFIX_BMD = "BMD - "
PREFIX_DRE = "DRE - "
PREFIX_LEVER = "Lever Machine - "
PREFIX_CENTRAL_SCAN = "Central Scan - "
PREFIX_PRECINCT_SCAN = "Precinct Scan - "

# List of all prefixes for easy iteration
ALL_PREFIXES = [
    PREFIX_MACHINE,
    PREFIX_BMD,
    PREFIX_DRE,
    PREFIX_LEVER,
    PREFIX_CENTRAL_SCAN,
    PREFIX_PRECINCT_SCAN,
]

# Prefixes that indicate machine-based marking (not hand-marked paper)
MACHINE_MARKING_PREFIXES = [
    PREFIX_MACHINE,
    PREFIX_BMD,
    PREFIX_DRE,
    PREFIX_LEVER,
]

# Prefixes that indicate scanner-based systems
SCANNER_PREFIXES = [
    PREFIX_CENTRAL_SCAN,
    PREFIX_PRECINCT_SCAN,
]


# ============================================================================
# EQUIPMENT CLASSIFICATION HELPERS
# ============================================================================

def strip_prefix(equipment_name):
    """
    Remove any equipment prefix from an equipment name.

    Args:
        equipment_name: Full equipment name (e.g., "Machine - ES&S ExpressVote")

    Returns:
        Equipment name without prefix (e.g., "ES&S ExpressVote")
    """
    if not equipment_name:
        return equipment_name

    for prefix in ALL_PREFIXES:
        if equipment_name.startswith(prefix):
            return equipment_name[len(prefix):]

    return equipment_name


def get_prefix(equipment_name):
    """
    Extract the prefix from an equipment name.

    Args:
        equipment_name: Full equipment name (e.g., "Machine - ES&S ExpressVote")

    Returns:
        The prefix if found (e.g., "Machine - "), or empty string if no prefix
    """
    if not equipment_name:
        return ""

    for prefix in ALL_PREFIXES:
        if equipment_name.startswith(prefix):
            return prefix

    return ""


def has_prefix(equipment_name, prefix):
    """
    Check if an equipment name starts with a specific prefix.

    Args:
        equipment_name: Full equipment name
        prefix: Prefix to check for (e.g., PREFIX_MACHINE)

    Returns:
        True if equipment name starts with the prefix, False otherwise
    """
    if not equipment_name or not prefix:
        return False

    return equipment_name.startswith(prefix)


def is_scanner_equipment(equipment_name):
    """
    Check if equipment is a scanner type (Central or Precinct Scan).

    Args:
        equipment_name: Full equipment name

    Returns:
        True if equipment is a scanner type, False otherwise
    """
    return any(has_prefix(equipment_name, prefix) for prefix in SCANNER_PREFIXES)


def is_machine_marking(equipment_name):
    """
    Check if equipment uses machine-based marking.

    Args:
        equipment_name: Full equipment name

    Returns:
        True if equipment uses machine marking, False otherwise
    """
    return any(has_prefix(equipment_name, prefix) for prefix in MACHINE_MARKING_PREFIXES)


def format_equipment_name(prefix, manufacturer, model):
    """
    Format an equipment name, avoiding duplicate vendor names.

    Removes manufacturer name from the start of model if it's duplicated.
    For example: manufacturer="AVM", model="AVM Manual" → "AVM Manual" (not "AVM AVM Manual")
    Also handles: manufacturer="Premier (Diebold)", model="Premier Central Scan" → "Premier (Diebold) Central Scan"

    Args:
        prefix: Equipment type prefix (e.g., PREFIX_LEVER)
        manufacturer: Manufacturer name (e.g., "AVM")
        model: Model name (e.g., "AVM Manual")

    Returns:
        Formatted equipment name (e.g., "Lever Machine - AVM Manual")
    """
    if not manufacturer or not model:
        if manufacturer:
            return f"{prefix}{manufacturer}"
        return prefix.rstrip(" - ")

    # Remove manufacturer from start of model if duplicated
    # Handle various separators and case variations
    model_clean = model.strip()
    manufacturer_clean = manufacturer.strip()

    # Check if model starts with exact manufacturer (with various separators)
    if model_clean.startswith(f"{manufacturer_clean} "):
        # Remove "Manufacturer " from start of model
        model_clean = model_clean[len(manufacturer_clean):].lstrip()
    elif model_clean.startswith(f"{manufacturer_clean}-"):
        # Remove "Manufacturer-" from start of model
        model_clean = model_clean[len(manufacturer_clean):].lstrip("-").lstrip()
    else:
        # Check if model starts with first word of manufacturer (for cases like "Premier (Diebold)")
        # Extract first word from manufacturer (everything before space or parenthesis)
        first_word = manufacturer_clean.split()[0].split('(')[0]
        if first_word and model_clean.startswith(f"{first_word} "):
            # Remove first word from model
            model_clean = model_clean[len(first_word):].lstrip()

    # Combine manufacturer and cleaned model
    return f"{prefix}{manufacturer_clean} {model_clean}"
