from __future__ import annotations

from typing import Dict, Callable, Type, List, Tuple

import constants
import util

from cell import Cell


def scrape_otz(service, spreadsheet_id: str, character_type: str, min_characters: int, min_universals) -> Dict:
    if character_type not in constants.CHARACTER_TYPES:
        raise ValueError(f'character_type must be in {constants.CHARACTER_TYPES}!')

    print(f"Starting scraping Otzdarva spreadsheet for {character_type.capitalize()}...")

    is_survivor = character_type == 'survivor'

    characters_info = _scrape_characters(service, spreadsheet_id, is_survivor, min_characters)
    universal_perks_info = _scrape_universal_perks(service, spreadsheet_id, is_survivor, min_universals)
    guides_info = _scrape_guide_links(service, spreadsheet_id, is_survivor)

    return {"characters": characters_info} | {"universals": universal_perks_info} | {"guides": guides_info}


def _scrape_characters(service, spreadsheet_id: str, is_survivor: bool, min_characters: int) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS
    start = Cell(sheet_constants['character_col_start'], sheet_constants['start'])

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

    def key_extract_func(cell):
        return cell['name'].removeprefix("The ")

    def key_req_func(d):
        return d['name']

    return _scrape_sheet(service=service,
                         spreadsheet_id=spreadsheet_id,
                         is_survivor=is_survivor,
                         sheet_name=sheet_constants['sheet_name'],
                         search_for_unknown=True,
                         min_search_amount=min_characters,
                         start=start,
                         next_start_func=next_start_func,
                         cell_dict_func=_get_cells_for_character,
                         key_req_func=key_req_func,
                         key_extract_func=key_extract_func,
                         data_extract_func=data_extract_func
                         )


def _scrape_universal_perks(service, spreadsheet_id: str, is_survivor: bool, min_universals: int) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS
    start = Cell(sheet_constants['base_perks_start_col'], sheet_constants['base_perks_start_row'])

    def data_extract_func(dt: str, c: dict) -> (dict, list[Type[str | list]]):
        if dt == "perk_tier":
            return c['userEnteredFormat']['backgroundColorStyle']['rgbColor'], str
        elif dt == "perk_name":
            return c['effectiveValue']['stringValue'], str

    return _scrape_sheet(service=service,
                         spreadsheet_id=spreadsheet_id,
                         is_survivor=is_survivor,
                         sheet_name=sheet_constants['sheet_name'],
                         search_for_unknown=True,
                         min_search_amount=min_universals,
                         start=start,
                         next_start_func=lambda cell, _: cell + 1,
                         cell_dict_func=lambda cell, _: util.BiDict({
                             "perk_name": cell >> 1,
                             "perk_tier": cell,
                         }),
                         key_req_func=lambda _: None,
                         key_extract_func=lambda cell: cell['perk_name'],
                         data_extract_func=data_extract_func
                         )


def _scrape_guide_links(service, spreadsheet_id: str, is_survivor: bool) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS
    guides = sheet_constants['guides']

    sheet_name = 'Survivor Sound & Stealth' if is_survivor else 'Killer Info'

    return _scrape_sheet(service=service,
                         spreadsheet_id=spreadsheet_id,
                         is_survivor=is_survivor,
                         sheet_name=sheet_name,
                         search_for_unknown=False,
                         min_search_amount=1,
                         start=min(list(guides.values())),
                         next_start_func=lambda cell, _: cell,  # don't need this, so might as well make it identity
                         cell_dict_func=lambda cell, _: guides,
                         key_req_func=lambda cell: None,
                         key_extract_func=lambda cell: None,
                         data_extract_func=lambda dt, c: (c['hyperlink'], str)
                         )[0]


def _scrape_sheet(service, spreadsheet_id: str, is_survivor: bool,
                  sheet_name: str,
                  search_for_unknown: bool,
                  min_search_amount: int,
                  start: Cell,
                  next_start_func: Callable[[Cell, int], Cell],
                  cell_dict_func: Callable[[Cell, bool], util.BiDict],
                  key_req_func: Callable[[dict], str | None],
                  key_extract_func: Callable[[dict], str | None],
                  data_extract_func: Callable[[str, dict], Tuple[dict, (Type[str] | Type[List])]],
                  ) -> Dict:
    # wow, this is alot of refactoring lmao
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS

    response, cell_structure = _send_request(service=service,
                                             spreadsheet_id=spreadsheet_id,
                                             start=start,
                                             sheet_name=sheet_name,
                                             search_for_unknown=search_for_unknown,
                                             min_known_search_size=min_search_amount,
                                             is_survivor=is_survivor,
                                             next_start_func=next_start_func,
                                             cell_dict_func=cell_dict_func,
                                             key_func=key_req_func)

    info = _extract_data_from_response(response=response,
                                       start=start,
                                       cell_structure=cell_structure,
                                       next_start_func=next_start_func,
                                       data_extract_func=data_extract_func,
                                       key_func=key_extract_func
                                       )

    return info


def _send_request(service, spreadsheet_id: str, start: Cell, sheet_name: str, search_for_unknown: bool,
                  min_known_search_size: int, is_survivor: bool,
                  next_start_func: Callable[[Cell, int], Cell],
                  cell_dict_func: Callable[[Cell, bool], util.BiDict],
                  key_func: Callable[[dict], str | None]
                  ):
    # I've tried other ways of doing this, being more "economical" in terms of specifying which cells are requested,
    # but this genuinely seems like the best solution for reducing API calls (for each character there's 2 cells wasted)
    request = []
    relevant_cells = {}

    curr = start
    i = 0

    # "known"
    for i in range(min_known_search_size):
        cells = cell_dict_func(curr, is_survivor)

        cell_ranges = util.flatten_list(cells.values())

        cell_min, cell_max = min(cell_ranges), max(cell_ranges)

        request.append(f"{sheet_name}!{cell_min}:{cell_max}")

        assignment = key_func(cells)
        relevant_cells[assignment if assignment is not None else i] = cells
        curr = next_start_func(curr, i)

    response = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=request,
                                          includeGridData=True).execute()

    response = response['sheets'][0]['data']

    # "unknown"
    i += 1

    # TODO: Refactor below code and above into functions for re-use (the two look suspiciously similar...)
    while search_for_unknown:
        cells = cell_dict_func(curr, is_survivor)
        cell_ranges = util.flatten_list(cells.values())
        cell_min, cell_max = min(cell_ranges), max(cell_ranges)

        request = [f"{sheet_name}!{cell_min}:{cell_max}"]
        resp = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=request, includeGridData=True).execute()

        if 'effectiveValue' not in resp['sheets'][0]['data'][0]['rowData'][0]['values'][0]:  # jesus christ google lmao
            search_for_unknown = False
            break

        response = response + resp['sheets'][0]['data']

        assignment = key_func(cells)
        relevant_cells[assignment if assignment is not None else i] = cells
        curr = next_start_func(curr, i)

        i += 1

    return response, relevant_cells


def _extract_data_from_response(response: dict,
                                start: Cell,
                                cell_structure: dict,
                                next_start_func: Callable[[Cell, int], Cell],
                                data_extract_func: Callable[[str, dict], Tuple[dict, (Type[str] | Type[List])]],
                                key_func: Callable[[dict], str | None]) -> dict:
    infos = {}

    curr = start

    for i, (relevant_cells, character_response_data) in enumerate(
            zip(cell_structure.values(), response)):
        info = {}

        relevant_cells = relevant_cells.inverse

        character_cell_sheets = character_response_data['rowData']

        for row_idx, row in enumerate(character_cell_sheets):
            row = row['values']
            for col_idx, col in enumerate(row):
                curr_cell = (curr >> col_idx) + row_idx

                if curr_cell in relevant_cells:
                    data_type = relevant_cells[curr_cell]
                    extracted, type_ = data_extract_func(data_type, col)

                    if type_ == list:
                        info.setdefault(data_type, []).append(extracted)
                    else:
                        info[data_type] = extracted

        assignment = key_func(info)
        infos[assignment if assignment is not None else i] = info
        curr = next_start_func(curr, i)

    return infos


def _get_next_character_start(curr: Cell,
                              index: int,
                              row_skip: int,
                              col_skip: int = constants.GLOBAL_CONSTANTS['col_skip'],
                              characters_per_row: int = constants.GLOBAL_CONSTANTS['characters_per_row']) -> Cell:
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
