"""
Shared constants for voting equipment classification across all analysis scripts.

This module provides consistent equipment classifications used throughout the
codebase for categorizing and analyzing voting equipment.
"""

# Maps equipment model substring to family name for grouping similar systems
# Used to classify equipment into generations/families for analysis
EQUIPMENT_FAMILIES = {
    # ES&S families (most specific first to avoid false matches)
    'ES&S DS Central': 'ES&S DS Central',
    'ES&S DS300': 'ES&S DS300',
    'ES&S DS200': 'ES&S DS200 Generation',
    'ES&S DS': 'ES&S DS200 Generation',  # Catches collapsed "ES&S DS"
    'ES&S ExpressVote': 'ES&S DS200 Generation',
    'ES&S Model 100': 'ES&S Model 100 Generation',
    'ES&S Model 115': 'ES&S Model 100 Generation',
    'ES&S Model 150': 'ES&S Model 100 Generation',
    'ES&S Model 315': 'ES&S Model 100 Generation',
    'ES&S Model 550': 'ES&S Model 100 Generation',
    'ES&S Model 650': 'ES&S Model 100 Generation',
    'ES&S AutoMARK': 'ES&S Model 100 Generation',
    'ES&S iVotronic': 'iVotronic',
    'ES&S InkaVote': 'InkaVote',
    'ES&S Votomatic': 'Votomatic',
    'ES&S OpTech 2': 'Optech Eagle Generation',

    # AccuVote families
    'AccuVote TS': 'AccuVote TS',  # Must come before AccuVote OS to catch TSX
    'AccuVote OS': 'AccuVote OS',
    'Premier (Diebold) Premier Central Scan': 'AccuVote OS',

    # Dominion ImageCast family
    'Dominion ImageCast': 'Dominion ImageCast',

    # Clear Ballot family
    'Clear Ballot': 'Clear Ballot',

    # DFM Mark-a-Vote
    'DFM Mark-a-Vote': 'DFM Mark-a-Vote',

    # Hart families
    'Hart InterCivic Ballot Now': 'Hart eSeries',
    'Hart InterCivic eScan': 'Hart eSeries',
    'Hart InterCivic eSlate': 'Hart eSeries',
    'Hart InterCivic Vanguard': 'Hart Vanguard',
    'Hart InterCivic Verity': 'Hart Verity',

    # Los Angeles County
    'Los Angeles County MTS': 'Los Angeles County MTS',
    'Los Angeles County VSAP': 'Los Angeles County VSAP',

    # Optech families
    'Optech IIIP-Eagle': 'Optech Eagle Generation',
    'Optech 400C': 'Optech Insight Generation',
    'Optech IV-C': 'Optech Insight Generation',
    'Optech Insight': 'Optech Insight Generation',

    # Unisyn families
    'Unisyn OpenElect OVCS': 'Unisyn Generation 1',
    'Unisyn OpenElect OVO': 'Unisyn Generation 1',
    'Unisyn OpenElect OVI': 'Unisyn Generation 1',
    'Unisyn OpenElect FVS': 'Unisyn Generation 2',
    'Unisyn OpenElect FVT': 'Unisyn Generation 2',

    # VotingWorks
    'VotingWorks': 'VotingWorks',
}
