from scrapers.cell import Cell
import util

CHARACTER_TYPES = ["killer", "survivor"]

DBD_WIKI_BASE_LINK = 'https://deadbydaylight.fandom.com/wiki/'

GLOBAL_CONSTANTS = {
    "character_col_start": 'B',
    "characters_per_row": 5,
    "col_skip": 4,
    "row_skip": 13,
    "base_perks_start_row": 21,
}

SURVIVOR_CONSTANTS = GLOBAL_CONSTANTS | {
    "sheet_name": "Survivor Info",

    "start": 19,
    "character_row_skip": 12,
    "base_perks_start_col": 'W',
    "guides_start": Cell('D', 4),

    "misc": util.BiDict({

    })
}

KILLER_CONSTANTS = GLOBAL_CONSTANTS | {
    "sheet_name": "Killer Info",

    "start": 20,
    "character_row_skip": 13,
    "base_perks_start_col": 'V',
    "guides_start": Cell('N', 4),

    "misc": util.BiDict({
        "last_updated": Cell('G', 4)
    })
}
