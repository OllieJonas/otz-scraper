from scrapers.cell import Cell

CHARACTERS_PER_ROW = 5
CHARACTER_COL_SKIP = 4

CHARACTER_TYPES = ["killer", "survivor"]

GLOBAL_CONSTANTS = {
    "col_skip": 4,
    "row_skip": 13,
    "base_perks_start_row": 21,
}

SURVIVOR_CONSTANTS = GLOBAL_CONSTANTS | {
    "sheet_name": "Survivor Info",

    "guides": {
        "Survivor Sound & Stealth!D5": "sounds_survivor_pov",
        "Survivor Sound & Stealth!D8": "sounds_killer_pov",
    },

    "misc": {
        "Survivor Sound & Stealth!D12:D14": "noise_descs"
    },

    "start": 19,
    "character_row_skip": 12,
    "base_perks_start_col": 'W'
}

KILLER_CONSTANTS = GLOBAL_CONSTANTS | {
    "sheet_name": "Killer Info",

    "guides": {
        "Killer Info!N5": "latest_tier_list",
        "Killer Info!N8": "which_killer",
    },

    "misc": {

    },

    "start": 20,
    "base_perks_start_col": 'V',
    "character_row_skip": 13,
    "quiz_cell": Cell('N', 8),
    "latest_tier_list_cell": Cell('N', 5)
}
