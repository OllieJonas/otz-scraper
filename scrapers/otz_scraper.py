from __future__ import annotations

from typing import Dict, Callable, Type, List, Tuple

import constants
import util

from unidecode import unidecode

from cell import Cell


def scrape_otz(service, spreadsheet_id: str, character_type: str, min_characters: int, min_universals: int) -> Dict:
    if character_type not in constants.CHARACTER_TYPES:
        raise ValueError(f'character_type must be in {constants.CHARACTER_TYPES}!')

    print(f"Starting scraping Otzdarva spreadsheet for {character_type.capitalize()}...")

    is_survivor = character_type == 'survivor'

    characters_info = _scrape_characters(service, spreadsheet_id, is_survivor, min_characters)
    universal_perks_info = _scrape_universal_perks(service, spreadsheet_id, is_survivor, min_universals)
    guides_info = _scrape_guide_links(service, spreadsheet_id, is_survivor)
    misc_info = _scrape_misc(service, spreadsheet_id, is_survivor)

    return {"characters": characters_info} | \
           {"universals": universal_perks_info} | \
           {"guides": guides_info} | \
           {"misc": misc_info}


def _scrape_characters(service, spreadsheet_id: str, is_survivor: bool, min_characters: int) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS
    start = Cell(sheet_constants['character_col_start'], sheet_constants['start'])

    # closure (why do you need to make the row skip for killers and survivors different otz, why :(( )
    def next_start_func(cell, i):
        return _get_next_character_start(cell, i,
                                         row_skip=sheet_constants['character_row_skip'])

    def data_extract_func(dt: str, c: dict) -> (dict, list[Type[str | list]]):
        if dt == "perk_tiers":
            rgb: dict = c['userEnteredFormat']['backgroundColorStyle']['rgbColor']
            return util.rgb_dict_to_dict(rgb), list

        elif dt == "perk_names":
            return_dict = {
                'name': c['effectiveValue']['stringValue'].replace("Scourge Hook: ", "")
            }

            if is_survivor:
                return_dict['is_exhaustion_perk'] = 'borders' in c['effectiveFormat']

            return return_dict, list

        elif dt == "availability":
            rgb: dict = c['userEnteredFormat']['backgroundColorStyle']['rgbColor']

            return {'value': c['effectiveValue']['stringValue'],
                    'colour': util.rgb_dict_to_dict(rgb)}, str
        else:
            return unidecode(c['effectiveValue']['stringValue'].replace("TR", "").strip()), str

    def key_extract_func(cell):
        return cell['name'].removeprefix("The ")  # for killer, just to keep things universal

    def key_req_func(d):
        return d['name']

    sheet = _scrape_sheet(service=service,
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

    # grouping perk_tiers and perk_names, could probably rework code to make this work but that's more effort than
    # just hacking it at the end lmao
    for name, character in sheet.items():
        perks = []
        for tier, info in zip(character['perk_tiers'], character['perk_names']):
            perks.append({**info, 'tier': tier})

        character['perks'] = perks

        del character['perk_tiers']
        del character['perk_names']

    return sheet


def _scrape_universal_perks(service, spreadsheet_id: str, is_survivor: bool, min_universals: int) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS
    start = Cell(sheet_constants['base_perks_start_col'], sheet_constants['base_perks_start_row'])

    def data_extract_func(dt: str, c: dict) -> (dict, list[Type[str | list]]):
        if dt == "tier":
            return util.rgb_dict_to_dict(c['userEnteredFormat']['backgroundColorStyle']['rgbColor']), str
        elif dt == "name":
            return c['effectiveValue']['stringValue'].replace("Scourge Hook: ", ""), str

    return _scrape_sheet(service=service,
                         spreadsheet_id=spreadsheet_id,
                         is_survivor=is_survivor,
                         sheet_name=sheet_constants['sheet_name'],
                         search_for_unknown=True,
                         min_search_amount=min_universals,
                         start=start,
                         next_start_func=lambda cell, _: cell + 1,
                         cell_dict_func=lambda cell, _: util.BiDict({
                             "name": cell >> 1,
                             "tier": cell,
                         }),
                         key_req_func=lambda _: None,
                         key_extract_func=lambda cell: cell['name'],
                         data_extract_func=data_extract_func
                         )


def _scrape_guide_links(service, spreadsheet_id: str, is_survivor: bool) -> List:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS
    guides_start = sheet_constants['guides_start']

    sheet_name = 'Survivor Sound & Stealth' if is_survivor else 'Killer Info'

    def data_extract_func(dt, c):
        if dt == "title" or dt == "link_text":
            return c['effectiveValue']['stringValue'], str
        else:
            return c['hyperlink'], str

    return list(_scrape_sheet(service=service,
                              spreadsheet_id=spreadsheet_id,
                              is_survivor=is_survivor,
                              sheet_name=sheet_name,
                              search_for_unknown=False,
                              min_search_amount=2,
                              start=guides_start,
                              next_start_func=lambda cell, _: cell + (4 if is_survivor else 3),
                              cell_dict_func=lambda cell, _: util.BiDict({
                                  "title": cell,
                                  "hyperlink": cell + 1,
                                  "link_text": cell + 1,
                              }),
                              key_req_func=lambda cell: None,
                              key_extract_func=lambda cell: None,
                              data_extract_func=data_extract_func
                              ).values())


def _scrape_misc(service, spreadsheet_id: str, is_survivor: bool) -> Dict:
    sheet_constants = constants.SURVIVOR_CONSTANTS if is_survivor else constants.KILLER_CONSTANTS

    misc = sheet_constants['misc']

    if len(misc) == 0:
        return {}

    response = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=list(misc.values()),
                                          includeGridData=True).execute()

    response = response['sheets'][0]['data']

    def data_extract_func(dt, c):
        if dt == "last_updated":  # always true at the moment, done this to make it obvious how to change stuff
            return c['effectiveValue']['numberValue'], str

    return _extract_data_from_response(response=response,
                                       start=min(list(misc.values())),
                                       cell_structure={0: misc},
                                       next_start_func=lambda cell, _: cell,
                                       data_extract_func=data_extract_func,
                                       key_func=lambda cell: None)[0]


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
    """
    Scrape a given portion of a spreadsheet, based on certain rules.

    More specifically, this works in two parts: Gathering the cell information from the Google Sheet, then extracting
    that information from the response JSON from Google into something that's usable (i.e. based on a certain structure
    that's pre-determined).

    SENDING THE REQUEST
    -------------------------
    Starts at a given cell (:param start), then uses the :param `cell_dict_func` to map that starting cell to the cells
    you wish to gather information about (the result of this is now referred to as 'cell_structure').
    Fetch cells between the min and max of cell_structure (from Google), apply the :param key_req_func to cell_struct
    (extracting a key from relevant_cells). Repeat this for the :param min_search_amount (the "known" portion,
    see comment in args of main for more info).

    Once this is done, we then repeat a similar process any number of times (whilst the starting cell isn't empty on
    Google Sheets), adding the responses for these into the known search results.

    Once the starting cell is empty, then return both the response from Google and cell_structure.

    EXTRACTING DATA
    -------------------------
    From the previous results, we get a "raw" response from Google, and a dictionary mapping cells (in A1 notation) to
    descriptors of what that information is. Extracting the data simply involves replacing all A1 notation with values
    from the raw response.

    :param service: Google Sheets API service
    :param spreadsheet_id: Sheet ID
    :param is_survivor: Whether we're doing this for Survivors or Killers
    :param sheet_name: Name of the sheet (Used pretty much exclusively for Survivor Guides being on a different sheet)
    :param search_for_unknown: Whether to search for "unknown"
    :param min_search_amount: Amount of "known" searches
    :param start: Starting cell
    :param next_start_func: Function mapping current cell and iteration no to next cell

    :param cell_dict_func:  Function mapping starting cell and is_survivor to a dictionary mapping cells to information
                            descriptors (eg. (cell, is_survivor) -> {"name": cell, "tier": cell >> 1})

    :param key_req_func: Function that illustrates what key to use for the relevant_cells return value. If None is the
                         return value, it will use the index of the current search.

                            For example:
                                (cell_dict_func=(cell, _) -> {"name": cell, "tier": cell >> 1},
                                key_req_func=(dict) -> dict['tier']) =>
                                 relevant_cells={cell >> 1: {"name": cell, "tier": cell >> 1}}

    :param key_extract_func:  Pretty much identical usage to key_req_func, but used in the data extraction portion.

    :param data_extract_func: Function that maps what information to extract for each cell, based on some data_type.
                              data_type (str) comes from cell_structure, cell (dict) comes from the raw response.
                              It would probably be easiest to see some of the above examples of this function to
                              see how it should be used.

    :return: A map of data_types in cells to the information that's stored in the spreadsheet.
    """
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
    cell_structure = {}

    curr = start
    i = 0

    # "known"
    for i in range(min_known_search_size):
        cells = cell_dict_func(curr, is_survivor)

        cell_ranges = util.flatten_list(cells.values())

        cell_min, cell_max = min(cell_ranges), max(cell_ranges)

        request.append(f"{sheet_name}!{cell_min}:{cell_max}")

        assignment = key_func(cells)
        cell_structure[assignment if assignment is not None else i] = cells
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

        root_cell = resp['sheets'][0]['data'][0]['rowData'][0]['values'][0]

        if 'effectiveValue' not in root_cell and \
                ('userEnteredFormat' in root_cell and not root_cell['userEnteredFormat']['backgroundColor']):
            search_for_unknown = False
            break

        response = response + resp['sheets'][0]['data']

        assignment = key_func(cells)
        cell_structure[assignment if assignment is not None else i] = cells
        curr = next_start_func(curr, i)

        i += 1

    return response, cell_structure


def _extract_data_from_response(response: dict,
                                start: Cell,
                                cell_structure: dict,
                                next_start_func: Callable[[Cell, int], Cell],
                                data_extract_func: Callable[[str, dict], Tuple[dict, (Type[str] | Type[List])]],
                                key_func: Callable[[dict], str | None]) -> dict:
    infos = {}

    curr = start

    for i, (relevant_cells, response_data) in enumerate(
            zip(cell_structure.values(), response)):
        info = {}

        relevant_cells = relevant_cells.inverse

        cell_sheets = response_data['rowData']

        for row_idx, row in enumerate(cell_sheets):
            row = row['values']
            for col_idx, col in enumerate(row):
                curr_cell = (curr >> col_idx) + row_idx

                if curr_cell in relevant_cells:

                    data_type = relevant_cells[curr_cell]

                    if not type(data_type) == list:
                        data_type = [data_type]

                    for dt in data_type:
                        extracted, type_ = data_extract_func(dt, col)

                        if type_ == list:
                            info.setdefault(dt, []).append(extracted)
                        else:
                            info[dt] = extracted

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


def perk_colour_to_hex(perk_colour: dict) -> str:
    return util.rgb_to_hex(perk_colour.get('red', 0.0), perk_colour.get('green', 0.0), perk_colour.get('blue', 0.0))
