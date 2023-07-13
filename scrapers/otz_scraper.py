from __future__ import annotations

import functools
from typing import Dict, Callable, Type, List, Tuple

import constants
import util

from cell import Cell


def scrape_otz(service, spreadsheet_id: str, character_type: str, min_characters: int, min_universals) -> Dict:
    if character_type not in constants.CHARACTER_TYPES:
        raise ValueError(f'character_type must be in {constants.CHARACTER_TYPES}!')

    is_survivor = character_type == 'survivor'

    characters_info = _scrape_characters(service, spreadsheet_id, is_survivor, min_characters)
    universal_perks_info = _scrape_universal_perks(service, spreadsheet_id, is_survivor, min_universals)

    util.pretty_print(characters_info)

    guides_info = _scrape_guide_links(service, spreadsheet_id, is_survivor)


def _scrape_characters(service, spreadsheet_id: str, is_survivor: bool, min_characters: int) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS
    start = Cell('B', sheet_constants['start'])

    # closure (why do you need to make the row skip for killers and survivors different otz, why :(( )
    def next_start_func(cell, i):
        return _get_next_character_start(cell, i,
                                         row_skip=sheet_constants['character_row_skip'])

    def data_extract_func(dt: str, c: dict) -> (dict, list[Type[str | list]]):
        if dt == "perk_tiers":
            return {'value': c['userEnteredFormat']['backgroundColorStyle']['rgbColor']}, list

        elif dt == "perk_names":
            return_dict = {
                'value': c['effectiveValue']['stringValue']
            }

            if is_survivor:
                return_dict['is_exhaustion_perk'] = 'borders' in c['effectiveFormat']

            return return_dict, list

        else:
            return c['effectiveValue']['stringValue'].replace("TR", "").strip(), str

    def key_extract_func(cell): return cell['name'].removeprefix("The ")

    def key_req_func(d): return d['name']

    return _scrape_perks(service=service,
                         spreadsheet_id=spreadsheet_id,
                         is_survivor=is_survivor,
                         min_search_amount=min_characters,
                         start=start,
                         next_start_func=next_start_func,
                         cell_dict_func=_get_cells_for_character,
                         key_req_func=key_req_func,
                         key_extract_func=key_extract_func,
                         handling_func=data_extract_func
                         )


def _scrape_universal_perks(service, spreadsheet_id: str, is_survivor: bool, min_universals: int) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS
    start = Cell(sheet_constants['base_perks_start_col'], sheet_constants['base_perks_start_row'])

    def data_extract_func(dt: str, c: dict) -> (dict, list[Type[str | list]]):
        if dt == "perk_tier":
            return c['userEnteredFormat']['backgroundColorStyle']['rgbColor'], str
        elif dt == "perk_name":
            return c['effectiveValue']['stringValue'], str

    return _scrape_perks(service=service,
                         spreadsheet_id=spreadsheet_id,
                         is_survivor=is_survivor,
                         min_search_amount=min_universals,
                         start=start,
                         next_start_func=lambda cell, _: cell + 1,
                         cell_dict_func=lambda cell, _: util.BiDict({
                            "perk_tier": cell,
                            "perk_name": cell >> 1
                         }),
                         key_req_func=lambda _: None,
                         key_extract_func=lambda cell: cell['perk_name'],
                         handling_func=data_extract_func
                         )


def _scrape_perks(service, spreadsheet_id: str, is_survivor: bool, min_search_amount: int, start: Cell,
                  next_start_func: Callable[[Cell, int], Cell],
                  cell_dict_func: Callable[[Cell, bool], util.BiDict],
                  key_req_func: Callable[[dict], str | None],
                  key_extract_func: Callable[[dict], str | None],
                  handling_func: Callable[[str, dict], Tuple[dict, (Type[str] | Type[List])]],
                  ):
    # wow this is alot of refactoring lmao
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS

    response, cell_structure = _send_request(service=service,
                                             spreadsheet_id=spreadsheet_id,
                                             start=start,
                                             sheet_constants=sheet_constants,
                                             min_search_amount=min_search_amount,
                                             is_survivor=is_survivor,
                                             next_start_func=next_start_func,
                                             cell_dict_func=cell_dict_func,
                                             key_func=key_req_func)

    characters_info = _extract_data_from_response(response=response,
                                                  start=start,
                                                  cell_structure=cell_structure,
                                                  next_start_func=next_start_func,
                                                  handling_func=handling_func,
                                                  key_func=key_extract_func
                                                  )

    return characters_info


def _scrape_guide_links(service, spreadsheet_id: str, is_survivor: bool):
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS

    return {}


def _send_request(service, spreadsheet_id: str, start: Cell, sheet_constants: dict,
                  min_search_amount: int, is_survivor: bool,
                  next_start_func: Callable[[Cell, int], Cell],
                  cell_dict_func: Callable[[Cell, bool], util.BiDict],
                  key_func: Callable[[dict], str | None]
                  ):
    # I've tried other ways of doing this, being more "economical" in terms of specifying which cells are requested,
    # but this genuinely seems like the best solution for reducing API calls (for each character there's 2 cells wasted)

    sheet_name = sheet_constants['sheet_name']

    request = []
    character_cells = {}

    curr = start

    i = 0

    # "known"
    for i in range(min_search_amount):
        cells = cell_dict_func(curr, is_survivor)

        cell_ranges = util.flatten_list(cells.values())

        cell_min, cell_max = min(cell_ranges), max(cell_ranges)

        request.append(f"{sheet_name}!{cell_min}:{cell_max}")

        assignment = key_func(cells)

        if assignment is None:
            assignment = i

        character_cells[assignment] = cells
        curr = next_start_func(curr, i)

    response = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=request,
                                          includeGridData=True).execute()
    response = response['sheets'][0]['data']

    # "unknown" characters beyond this
    empty = False
    i += 1

    # TODO: Refactor below code and above into functions for re-use (the two look suspiciously similar...)
    while not empty:
        cells = cell_dict_func(curr, is_survivor)
        cell_ranges = util.flatten_list(cells.values())
        cell_min, cell_max = min(cell_ranges), max(cell_ranges)

        request = [f"{sheet_name}!{cell_min}:{cell_max}"]
        resp = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=request, includeGridData=True).execute()

        if 'effectiveValue' in resp['sheets'][0]['data'][0]['rowData'][0]['values'][0]:
            response = response + resp['sheets'][0]['data']

            assignment = key_func(cells)

            if assignment is None:
                assignment = i

            character_cells[assignment] = cells
            curr = next_start_func(curr, i)

            i += 1
        else:
            empty = True

    return response, character_cells


def _extract_data_from_response(response: dict,
                                start: Cell,
                                cell_structure: dict,
                                next_start_func: Callable[[Cell, int], Cell],
                                handling_func: Callable[[str, dict], Tuple[dict, (Type[str] | Type[List])]],
                                key_func: Callable[[dict], str | None]) -> dict:
    characters_info = {}

    curr = start

    for i, (relevant_cells, character_response_data) in enumerate(
            zip(cell_structure.values(), response)):
        character_info = {}

        relevant_cells = relevant_cells.inverse

        character_cell_sheets = character_response_data['rowData']

        for row_idx, row in enumerate(character_cell_sheets):
            row = row['values']
            for col_idx, col in enumerate(row):
                curr_cell = (curr >> col_idx) + row_idx
                if curr_cell in relevant_cells:
                    data_type = relevant_cells[curr_cell]
                    extracted, type_ = handling_func(data_type, col)

                    if type_ == list:
                        character_info.setdefault(data_type, []).append(extracted)
                    else:
                        character_info[data_type] = extracted

        assignment = key_func(character_info)
        characters_info[assignment if assignment is not None else i] = character_info
        curr = next_start_func(curr, i)

    return characters_info


def _get_cell_for_universal(start: Cell) -> util.BiDict:
    return util.BiDict({
        "perk_tier": start,
        "perk_name": start >> 1
    })


def _get_next_character_start(curr: Cell,
                              index: int,
                              row_skip: int,
                              col_skip: int = 4,
                              characters_per_row: int = constants.CHARACTERS_PER_ROW) -> Cell:
    return curr >> col_skip if (index + 1) % characters_per_row != 0 \
        else (curr << (col_skip * (characters_per_row - 1))) + row_skip


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
