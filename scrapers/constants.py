from scrapers.cell import Cell

CHARACTERS_PER_ROW = 5
CHARACTER_COL_SKIP = 4
CHARACTER_ROW_SKIP = 13


GLOBAL_CONSTANTS = {
    "col_skip": 4,
    "row_skip": 13,
    "base_perks_start_row": 21,
}

SURVIVOR_CONSTANTS = GLOBAL_CONSTANTS | {
    "sheet_name": "Survivor Info",

    "start": 19,
    "character_row_skip": 12,
    "base_perks_start_col": 'X'
}

KILLER_CONSTANTS = GLOBAL_CONSTANTS | {
    "sheet_name": "Killer Info",

    "start": 20,
    "base_perks_start_col": 'W',
    "character_row_skip": 13,
    "quiz_cell": Cell('N', 8),
    "latest_tier_list_cell": Cell('N', 5)
}

SPREADSHEET_CONSTANTS = {

}