from typing import Dict

import constants
import util

from cell import Cell

CHARACTER_TYPES = ["killer", "survivor"]


def scrape_otz(service, spreadsheet_id: str, character_type: str, min_characters: int, min_universals) -> Dict:
    if character_type not in CHARACTER_TYPES:
        raise ValueError(f'character_type must be in {CHARACTER_TYPES}!')

    is_survivor = character_type == 'survivor'

    characters_info = _scrape_characters(service, spreadsheet_id, is_survivor, min_characters)
    universal_perks_info = _scrape_universal_perks(service, spreadsheet_id, is_survivor, min_universals)


def _scrape_characters(service, spreadsheet_id: str, is_survivor: bool, min_characters: int) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS

    sheet_name = sheet_constants['sheet_name']

    start_cell = Cell('B', sheet_constants['start'])  # need this for later
    curr = start_cell

    request = []
    character_cells = {}

    # I've tried other ways of doing this, being more "economical" in terms of specifying which cells are requested,
    # but this genuinely seems like the best solution for reducing API calls.

    # get "known" amount of minimum characters
    for i in range(min_characters + 1):
        cell_range, curr, relevant_cells = \
            _get_next_request(curr, i, is_survivor, sheet_constants['character_row_skip'])

        request.append(f"{sheet_name}!{cell_range[0]}:{cell_range[1]}")
        character_cells[relevant_cells['name']] = relevant_cells

    min_characters_response = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=request,
                                                         includeGridData=True).execute()

    # get "unknown" amount of characters beyond this

    response_data = min_characters_response['sheets'][0]['data']
    characters_info = {}
    curr = start_cell

    for i, (character_relevant_cells, character_response_data) in enumerate(
            zip(character_cells.values(), response_data)):
        character_name = ''
        character_info = {}

        curr_cell_start = character_relevant_cells['name']

        character_relevant_cells = character_relevant_cells.inverse
        character_cell_sheets = character_response_data['rowData']

        for row_idx, row in enumerate(character_cell_sheets):
            row = row['values']
            for col_idx, col in enumerate(row):
                curr_cell = (curr_cell_start >> col_idx) + row_idx

                if curr_cell in character_relevant_cells:
                    data_type = character_relevant_cells[curr_cell]

                    if data_type == "perk_tiers":
                        colour = col['userEnteredFormat']['backgroundColorStyle']['rgbColor']
                        character_info.setdefault(character_relevant_cells[curr_cell], []).append(colour)

                    elif data_type == "perk_names":
                        data = col['effectiveValue']['stringValue']

                        if is_survivor:
                            character_info.setdefault('is_exhaustion_perk', []) \
                                .append('borders' in col['effectiveFormat'])

                        character_info.setdefault(character_relevant_cells[curr_cell], []).append(data)

                    else:
                        data = col['effectiveValue']['stringValue']

                        if data_type == 'name':
                            character_name = data.removeprefix("The ")

                        if data_type == "terror_radius":
                            data = data.replace("TR", "").strip()

                        character_info[character_relevant_cells[curr_cell]] = data

        characters_info[character_name] = character_info

    return characters_info


def _scrape_universal_perks(service, spreadsheet_id: str, is_survivor: bool, min_universals: int) -> Dict:
    pass


def _scrape_guide_links(service, spreadsheet_id: str, is_survivor: bool):
    pass


def _get_cell_for_universal(start: Cell) -> util.BiDict:
    return util.BiDict({
        "perk_tier": start,
        "perk_name": start >> 1
    })


def _get_cells_for_character(start: Cell, is_survivor: bool) -> util.BiDict:
    # see Cell for operator overloading info and how this works
    cells = util.BiDict({
        "name": start,
        "availability": start + 9,
        "perk_tiers": ((start >> 1) + 1).range(6, skip=3),
        "perk_names": ((start >> 2) + 2).range(6, skip=3)
    })

    if is_survivor:
        cells["stealth"] = start + 10
        cells["noise"] = (start >> 1) + 10
        cells["cries"] = (start >> 2) + 10
    else:
        cells["movement_speed"] = start + 10
        cells["terror_radius"] = (start >> 2) + 10

    return cells


def _get_next_character_start(curr: Cell,
                              index: int,
                              col_skip: int = constants.CHARACTER_COL_SKIP,
                              row_skip: int = constants.CHARACTER_ROW_SKIP,
                              characters_per_row: int = constants.CHARACTERS_PER_ROW) -> Cell:
    if index == 0:
        return curr

    return curr >> col_skip if index % characters_per_row != 0 \
        else (curr << (col_skip * (characters_per_row - 1))) + row_skip


def _get_next_request(curr: Cell, index: int, is_survivor: bool, row_skip: int):
    start_cell = _get_next_character_start(curr, index, row_skip=row_skip)
    cells = _get_cells_for_character(curr, is_survivor)

    # this is weird but honestly the best solution imo here is to just get the entire character window (including
    # blank spaces) and deal with them in our code

    cells_ranges = util.flatten_list(list(cells.values()))

    cell_min = min(cells_ranges)
    cell_max = max(cells_ranges)

    return (cell_min, cell_max), start_cell, cells
