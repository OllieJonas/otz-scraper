from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from typing import Tuple

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import util
from character_scraper import scrape_characters_mt
from otz_scraper import scrape_otz
from perk_scraper import scrape_perks

KILLER_PERKS_URL = "https://deadbydaylight.fandom.com/wiki/Killer_Perks"
SURVIVOR_PERKS_URL = "https://deadbydaylight.fandom.com/wiki/Survivor_Perks"

# for Lore, Killer Power, etc.
KILLER_CHARACTERS_URL = "https://deadbydaylight.fandom.com/wiki/Killers"
SURVIVOR_CHARACTERS_URL = "https://deadbydaylight.fandom.com/wiki/Survivors"

OTZ_SPREADSHEET_ID = "1uk0OnioNZgLly_Y9pZ1o0p3qYS9-mpknkv3DlkXAxGA"
TEST_SPREADSHEET_ID = "1aNc3RqnjkAkxYX2msRzHahFVszkvCJl5PpR4ept7lpI"

# differences in names between Otz's spreadsheet and the Wiki.
SPREADSHEET_TO_WIKI_DISCREPANCIES = util.BiDict({
    # killer
    "Play With Your Food": "Play with Your Food",  # shape
    "Knockout": "Knock Out",  # cannibal
    "Barbecue and Chilli": "Barbecue & Chilli",  # cannibal
    "Pop Goes The Weasel": "Pop Goes the Weasel",  # clown
    "Hex: Blood Favor": "Hex: Blood Favour",  # blight
    "Scourge Hook: Monstrous Shrine": "Monstrous Shrine",  # universal

    # survivor
    "Self Care": "Self-Care",  # claudette
    "Wake up!": "Wake Up!",  # quentin
    "Mettle of  Man": "Mettle of Man",  # ash, 2 spaces between "of" and "Man"
    "For The People": "For the People",  # zarina
})


def main():
    """
    The purpose of this project is to generate JSON files containing information about Characters (Killers and
    Survivors), Perks.

    This project has been made to serve the web rendering of the Killer and Survivor Info portions of Otz's
    Quick Info Sheet for DBD.

    The spreadsheet in question can be found here: https://otzdarva.com/spreadsheet
    (or here: https://docs.google.com/spreadsheets/d/1uk0OnioNZgLly_Y9pZ1o0p3qYS9-mpknkv3DlkXAxGA/edit#gid=806953)
    """
    args = parse_args()

    prepare_final_json = args.prepare_final_json

    # needs to be True to have enough information to prepare final JSONs (if that's what you want to do)
    should_scrape_perks = args.scrape_perks or prepare_final_json
    should_scrape_characters = args.scrape_characters or prepare_final_json
    should_scrape_sheet = args.scrape_spreadsheet or prepare_final_json

    current_date = datetime.now().strftime('%d-%m-%Y')

    killer_perks = {}
    survivor_perks = {}

    killer_characters = {}
    survivor_characters = {}

    killer_spreadsheet = {}
    survivor_spreadsheet = {}

    if should_scrape_perks:
        killer_perks = scrape_perks(KILLER_PERKS_URL)
        survivor_perks = scrape_perks(SURVIVOR_PERKS_URL)

        if not prepare_final_json:
            save_json("perks", survivor_perks | killer_perks, current_date)

    if should_scrape_characters:
        killer_characters = scrape_characters_mt("Killers", no_workers=args.no_workers)
        survivor_characters = scrape_characters_mt("Survivors", no_workers=args.no_workers)

        if not prepare_final_json:
            save_json("characters", survivor_characters | killer_characters, current_date)

    if should_scrape_sheet:
        credentials = Credentials.from_service_account_file(args.creds_path)
        service = build('sheets', 'v4', credentials=credentials)

        killer_spreadsheet = scrape_otz(service, OTZ_SPREADSHEET_ID, 'killer',
                                        args.min_characters, args.min_universals)

        survivor_spreadsheet = scrape_otz(service, OTZ_SPREADSHEET_ID, 'survivor',
                                          args.min_characters, args.min_universals)

        if not prepare_final_json:
            save_json("killer_spreadsheet", killer_spreadsheet, current_date)
            save_json("survivor_spreadsheet", survivor_spreadsheet, current_date)

    if prepare_final_json:
        perks, characters, spreadsheets = transform_dicts(survivor_perks=survivor_perks,
                                                          survivor_characters=survivor_characters,
                                                          survivor_spreadsheet=survivor_spreadsheet,
                                                          killer_perks=killer_perks,
                                                          killer_characters=killer_characters,
                                                          killer_spreadsheet=killer_spreadsheet,
                                                          current_date=current_date)

        save_json('perks', perks, current_date)
        save_json('characters', characters, current_date)
        save_json('spreadsheet', spreadsheets, current_date)


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
                perk_name = SPREADSHEET_TO_WIKI_DISCREPANCIES.get(perk['name'], perk['name'])
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
            perk_name = SPREADSHEET_TO_WIKI_DISCREPANCIES.get(perk['name'], perk['name'])
            perk['name'] = perk_name
            perk['icon'] = perks['All'][perk_name]['icon']
            transformed_universals[perk_name] = perk

        transformed_spreadsheet['universals'] = transformed_universals

        return transformed_spreadsheet

    transformed_survivor_spreadsheet = transform_spreadsheet(survivor_perks, survivor_characters, survivor_spreadsheet)
    transformed_killer_spreadsheet = transform_spreadsheet(killer_perks, killer_characters, killer_spreadsheet)

    # capitalise Cries in survivors (can't do it in CSS because you end up with m/S in killers, which is v wrong)

    # accommodates Google Sheet's date storage stuff
    # counts days from 1-1-1900, -2 because Google counts Feb 29th 1900 & 2000 as dates, which didn't happen
    # fun fact: this is actually to maintain compatability with Excel, which previously did... * the more ya know *
    sheet_update = (datetime(1900, 1, 1) +
                    timedelta(days=killer_spreadsheet['misc']['last_updated'] - 2)).strftime("%d-%m-%Y")

    update_dict = {"last_updated": {"application": current_date, "spreadsheet": sheet_update}}

    guides_dict = {"guides": {"survivors": survivor_spreadsheet['guides'], "killers": killer_spreadsheet['guides']}}

    return {surv: survivor_perks} | {kill: killer_perks}, survivor_characters | killer_characters, \
           update_dict | guides_dict | {surv: transformed_survivor_spreadsheet} | {kill: transformed_killer_spreadsheet}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=None)
    parser.add_argument("--creds_path",
                        default=f"{util.one_dir_up()}/credentials.json",
                        type=str,
                        help='service account credentials path (for google sheets API)')

    # The Google Sheets API has a rate limit of 60 reqs/min per user. Unfortunately, we don't necessarily know how many
    # characters there are on the sheet. At time of writing (10/7/23), there are 32 killers and 32 survivors.
    # 32 killers + 38 survivors = 70 characters > 60 reqs/min, so we need to do some kind of batching.

    # We could update how many characters there are manually, but I don't really want to HAVE to keep
    # updating this each time.

    # We could figure this out by scraping a list of characters off the wiki, but this is a lot of effort, the sheet
    # may not be up-to-date, and, most importantly, it would create a dependency on the Characters' wiki page.

    # We could use the perk_scraper to figure it out, but I don't really want one scraper to be dependent on another.

    # There is already a function to figure out the cell for where the next character will be, but it feels inefficient,
    # annoying and hacky to just keep generating those to a reasonably high number (or even the entire spreadsheet)
    # and check whether anything is there.

    # The solution I've come up with is to specify a minimum number of characters, which will be checked no matter
    # what (referred to as "known"), and then check for any additional ones beyond that (referred to as "unknown").

    # Is it hacky? Yes. Does it scale? Absolutely not, but given DBD adds ~2 characters/month, it will work for now.
    parser.add_argument("--min-characters", default=32, type=int,
                        help='the minimum amount of characters to search for on the Otz spreadsheet.')
    parser.add_argument("--min-universals", default=12, type=int,
                        help='the minimum amount of universal (base) perks to search for on the Otz spreadsheet.')
    parser.add_argument("--no-workers", default=16, type=int,
                        help='number of workers to use for character scraper. '
                             'recommended amount is the number of cores you have (including hyper-threading); '
                             'any more may cause slowdown!')
    parser.add_argument("--prepare-final-json", default=True, type=bool,
                        help="Whether to collate information from characters, perks and spreadsheet to create a final"
                             "JSON file for front-end usage.")
    parser.add_argument("--scrape-perks", default=True, type=bool,
                        help="Whether to scrape the perks wiki page")
    parser.add_argument("--scrape-characters", default=True, type=bool,
                        help="Whether to scrape the characters wiki page")
    parser.add_argument("--scrape-spreadsheet", default=True, type=bool,
                        help="Whether to scrape the Otzdarva spreadsheet")

    return parser.parse_args()


def save_json(file_name, content, current_date):
    with open(f'{util.one_dir_up()}/out/archive/{file_name}_{current_date}.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

    with open(f'{util.one_dir_up()}/out/{file_name}_LATEST.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
