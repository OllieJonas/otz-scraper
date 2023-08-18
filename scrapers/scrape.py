from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from typing import Tuple

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from Levenshtein import distance

import util
from character_scraper import scrape_characters_mt
from otz_scraper import scrape_otz
from perk_scraper import scrape_perks

# # differences in names between Otz's spreadsheet and the Wiki.
# SPREADSHEET_TO_WIKI_DISCREPANCIES = util.BiDict({
#     # killer
#     "Play With Your Food": "Play with Your Food",  # shape
#     "Knockout": "Knock Out",  # cannibal
#     "Barbecue and Chilli": "Barbecue & Chilli",  # cannibal
#     "Pop Goes The Weasel": "Pop Goes the Weasel",  # clown
#     "Hex: Blood Favor": "Hex: Blood Favour",  # blight
#     "Scourge Hook: Monstrous Shrine": "Monstrous Shrine",  # universal
#
#     # survivor
#     "Self Care": "Self-Care",  # claudette
#     "Wake up!": "Wake Up!",  # quentin
#     "Mettle of  Man": "Mettle of Man",  # ash, 2 spaces between "of" and "Man"
#     "For The People": "For the People",  # zarina
# })
from scrapers import constants


def scrape_all(args):
    """
    The purpose of this project is to generate JSON files containing information about Characters (Killers and
    Survivors), Perks.

    This project has been made to serve the web rendering of the Killer and Survivor Info portions of Otz's
    Quick Info Sheet for DBD.

    The spreadsheet in question can be found here: https://otzdarva.com/spreadsheet
    (or here: https://docs.google.com/spreadsheets/d/1uk0OnioNZgLly_Y9pZ1o0p3qYS9-mpknkv3DlkXAxGA/edit#gid=806953)
    """
    prepare_final_json = args.prepare_final_json

    # needs to be True to have enough information to prepare final JSONs (if that's what you want to do)
    should_scrape_perks = args.scrape_perks or prepare_final_json
    should_scrape_characters = args.scrape_characters or prepare_final_json
    should_scrape_sheet = args.scrape_spreadsheet or prepare_final_json

    current_date = datetime.now().strftime('%d-%m-%Y')
    otz_spreadsheet_id = constants.OTZ_SPREADSHEET_ID

    killer_perks = {}
    survivor_perks = {}

    killer_characters = {}
    survivor_characters = {}

    killer_spreadsheet = {}
    survivor_spreadsheet = {}

    if should_scrape_perks:
        killer_perks = scrape_perks("Killers")
        survivor_perks = scrape_perks("Survivors")

        if not prepare_final_json:
            util.save_json("perks", survivor_perks | killer_perks, current_date)

    if should_scrape_characters:
        killer_characters = scrape_characters_mt("Killers", no_workers=args.no_workers)
        survivor_characters = scrape_characters_mt("Survivors", no_workers=args.no_workers)

        if not prepare_final_json:
            util.save_json("characters", survivor_characters | killer_characters, current_date)

    if should_scrape_sheet:
        credentials = Credentials.from_service_account_file(args.creds_path)
        service = build('sheets', 'v4', credentials=credentials)

        killer_spreadsheet = scrape_otz(service, otz_spreadsheet_id, 'killer',
                                        args.min_characters, args.min_universals)

        survivor_spreadsheet = scrape_otz(service, otz_spreadsheet_id, 'survivor',
                                          args.min_characters, args.min_universals)

        if not prepare_final_json:
            util.save_json("killer_spreadsheet", killer_spreadsheet, current_date)
            util.save_json("survivor_spreadsheet", survivor_spreadsheet, current_date)

    if prepare_final_json:
        perks, characters, spreadsheets = transform_dicts(survivor_perks=survivor_perks,
                                                          survivor_characters=survivor_characters,
                                                          survivor_spreadsheet=survivor_spreadsheet,
                                                          killer_perks=killer_perks,
                                                          killer_characters=killer_characters,
                                                          killer_spreadsheet=killer_spreadsheet,
                                                          current_date=current_date)

        util.save_json('perks', perks, current_date)
        util.save_json('characters', characters, current_date)
        util.save_json('spreadsheet', spreadsheets, current_date)


def transform_dicts(survivor_perks: dict, survivor_characters: dict, survivor_spreadsheet: dict,
                    killer_perks: dict, killer_characters: dict, killer_spreadsheet: dict, current_date) -> \
        Tuple[dict, dict, dict]:
    """
    prepare Spreadsheet JSON for usage on the front-end.
    The idea of doing this here is to ensure that each scraper can act independently; this just does some extra
    processing once all of them have been scraped, and isn't necessary for this application to produce
    "correct" outputs.
    """
    surv = "survivors"
    kill = "killers"

    def create_character_from(perks, new_name, perk1, perk2, perk3, old_name="All", replace=False):
        perks[new_name] = {perk1: perks[old_name][perk1]} \
                          | {perk2: perks[old_name][perk2]} \
                          | {perk3: perks[old_name][perk3]}

        if replace:
            del perks[old_name][perk1]
            del perks[old_name][perk2]
            del perks[old_name][perk3]

    # add the stranger thing characters as their own unique perks
    create_character_from(killer_perks, "Demogorgon", "Jolt", "Fearmonger", "Claustrophobia")
    create_character_from(survivor_perks, "Steve", "Guardian", "Kinship", "Renewal")
    create_character_from(survivor_perks, "Nancy", "Situational Awareness", "Self-Aware", "Inner Healing")

    # Tapp gets saved with David King (isn't it like writing rule no 1 not to have characters w/ the same name smh BHVR)
    create_character_from(survivor_perks, "Tapp", "Tenacity", "Detective's Hunch", "Stake Out", old_name="David",
                          replace=True)

    sheet_perks = set(util.flatten_list(
        [perk['name'] for ch in survivor_spreadsheet['characters'].values() for perk in ch['perks']] +
        [perk['name'] for ch in killer_spreadsheet['characters'].values() for perk in ch['perks']] +
        list(survivor_spreadsheet['universals'].keys()) +
        list(killer_spreadsheet['universals'].keys())
    ))

    wiki_perks = set(util.flatten_list([list(ch.keys()) for ch in survivor_perks.values()] +
                                       [list(ch.keys()) for ch in killer_perks.values()]))

    perk_discrepancies = generate_perk_discrepancies_dict(sheet_perks, wiki_perks)

    # otz only uses the first names of survivors (with some exceptions)
    for old_key, value in survivor_characters.copy().items():

        if old_key == "David Tapp":  # david tapp is Tapp on the sheet, David in perks and David Tapp in chars. help :(
            new_key = old_key.split(" ")[1]
        else:
            new_key = old_key.split(" ")[0]

        survivor_characters[new_key] = value
        del survivor_characters[old_key]

    def transform_spreadsheet(perks, characters, spreadsheet):
        # for updating the output JSON with the wiki names, not the sheet ones
        transformed_spreadsheet = {"characters": {}}

        # character perks
        for name, sheet_character in spreadsheet['characters'].items():
            # this is bad
            if name == "Yun-Jin Lee":
                name = "Yun-Jin"

            elif name == "Nicholas":
                name = "Nicolas"

            transformed_perks = {}

            for perk in sheet_character['perks']:
                # perk comes from otz spreadsheet, perk name is used to access otz spreadsheet
                perk_name = perk_discrepancies.get(perk['name'], perk['name'])
                perk['icon'] = perks[name][perk_name]['icon']
                perk['name'] = perk_name
                transformed_perks[perk_name] = perk

            # capitalise "cries"
            if 'cries' in sheet_character:
                sheet_character['cries'] = sheet_character['cries'].title()

            sheet_character['name'] = name
            sheet_character['icon'] = characters[name]['icon']
            sheet_character['perks'] = transformed_perks
            transformed_spreadsheet['characters'][name] = sheet_character

        transformed_universals = {}

        for name, perk in spreadsheet['universals'].items():
            perk_name = perk_discrepancies.get(perk['name'], perk['name'])
            perk['name'] = perk_name
            perk['icon'] = perks['All'][perk_name]['icon']
            transformed_universals[perk_name] = perk

        transformed_spreadsheet['universals'] = transformed_universals

        return transformed_spreadsheet

    transformed_survivor_spreadsheet = transform_spreadsheet(survivor_perks, survivor_characters, survivor_spreadsheet)
    transformed_killer_spreadsheet = transform_spreadsheet(killer_perks, killer_characters, killer_spreadsheet)

    # accommodates Google Sheet's date storage stuff
    # counts days from 1-1-1900, -2 because Google counts Feb 29th 1900 & 2000 as dates, which didn't happen
    # fun fact: this is actually to maintain compatability with Excel, which previously did... * the more ya know *
    sheet_update = (datetime(1900, 1, 1) +
                    timedelta(days=killer_spreadsheet['misc']['last_updated'] - 2)).strftime("%d-%m-%Y")

    update_dict = {"last_updated": {"application": current_date, "spreadsheet": sheet_update}}

    guides_dict = {"guides": {"survivors": survivor_spreadsheet['guides'], "killers": killer_spreadsheet['guides']}}

    return {surv: survivor_perks} | {kill: killer_perks}, survivor_characters | killer_characters, \
           update_dict | guides_dict | {surv: transformed_survivor_spreadsheet} | {kill: transformed_killer_spreadsheet}


def generate_perk_discrepancies_dict(sheet_perks, wiki_perks):
    """
    There are some minor discrepancies between the Spreadsheet and the Wiki (e.g. Play With Your Food vs Play with
    Your Food). We could work these out manually (which would be a lot faster), but it makes the application brittle.

    This generates a dictionary mapping names in the sheet to names in the Wiki for any that aren't exactly the same
    using Levenshtein distance (see here: https://en.wikipedia.org/wiki/Levenshtein_distance).
    """
    discrepancies = {}

    for sheet_perk in sheet_perks:
        best_match = sheet_perk

        if sheet_perk not in wiki_perks:
            min_levenshtein = 100

            for wiki_perk in wiki_perks:
                leven = distance(sheet_perk, wiki_perk)
                if min_levenshtein >= leven:
                    min_levenshtein = leven
                    best_match = wiki_perk

            discrepancies[sheet_perk] = best_match

        wiki_perks.discard(best_match)  # get rid of it from wiki perks bc we already have a match

    return discrepancies
