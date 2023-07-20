from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Tuple

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import util
from character_scraper import scrape_characters
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

    # survivor
    "Self Care": "Self-Care",  # claudette
    "Wake up!": "Wake Up!",  # quentin
    "Mettle of  Man": "Mettle of Man",  # ash, 2 spaces between "of" and "Man"
    "For The People": "For the People",
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

    killer_perks = {}
    survivor_perks = {}

    killer_characters = {}
    survivor_characters = {}

    killer_spreadsheet = {}
    survivor_spreadsheet = {}

    if args.scrape_perks:
        killer_perks = scrape_perks(KILLER_PERKS_URL)
        survivor_perks = scrape_perks(SURVIVOR_PERKS_URL)

        save_json("killer_perks", killer_perks)
        save_json("survivor_perks", survivor_perks)

    if args.scrape_characters:
        killer_characters = scrape_characters("Killers")
        survivor_characters = scrape_characters("Survivors")

        save_json("killer_characters", killer_characters)
        save_json("survivor_characters", survivor_characters)

    if args.scrape_spreadsheet:
        credentials = Credentials.from_service_account_file(args.creds_path)
        service = build('sheets', 'v4', credentials=credentials)

        killer_spreadsheet = scrape_otz(service, OTZ_SPREADSHEET_ID, 'killer',
                                        args.min_characters, args.min_universals)

        survivor_spreadsheet = scrape_otz(service, OTZ_SPREADSHEET_ID, 'survivor',
                                          args.min_characters, args.min_universals)

        save_json("killer_spreadsheet", killer_spreadsheet)
        save_json("survivor_spreadsheet", survivor_spreadsheet)

    perks, characters, spreadsheets = transform_dicts(survivor_perks=survivor_perks,
                                                      survivor_characters=survivor_characters,
                                                      survivor_spreadsheet=survivor_spreadsheet,
                                                      killer_perks=killer_perks,
                                                      killer_characters=killer_characters,
                                                      killer_spreadsheet=killer_spreadsheet)

    save_json('perks', killer_perks)
    save_json('characters', killer_characters)
    save_json('spreadsheet', spreadsheets)


def transform_dicts(survivor_perks: dict, survivor_characters: dict, survivor_spreadsheet: dict,
                    killer_perks: dict, killer_characters: dict, killer_spreadsheet: dict) -> Tuple[dict, dict, dict]:
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

    # Tapp gets saved with David (isn't it like writing rule no 1 not to have characters w/ the same name smh BHVR)
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
        # character perks
        for name, sheet_character in spreadsheet['characters'].items():
            # this is bad
            if name == "Yun-Jin Lee":
                name = "Yun-Jin"

            for perk in sheet_character['perks']:
                # perk comes from otz spreadsheet
                # perk name is used to access otz spreadsheet
                perk_name = SPREADSHEET_TO_WIKI_DISCREPANCIES.get(perk['name'], perk['name'])
                perk['icon'] = perks[name][perk_name]['icon']

            sheet_character['icon'] = characters[name]['icon']

        for name, perk in spreadsheet['universals'].items():
            perk_name = SPREADSHEET_TO_WIKI_DISCREPANCIES.get(perk['name'], perk['name'])
            perk['icon'] = perks['All'][perk_name]['icon']

    transform_spreadsheet(survivor_perks, survivor_characters, survivor_spreadsheet)
    transform_spreadsheet(killer_perks, killer_characters, killer_spreadsheet)

    return {surv: survivor_perks} | {kill: killer_perks}, \
           {surv: survivor_characters} | {kill: killer_characters}, \
           {surv: survivor_spreadsheet} | {kill: killer_spreadsheet}


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
    parser.add_argument("--scrape-perks", default=True, type=bool,
                        help="Whether to scrape the perks wiki page")
    parser.add_argument("--scrape-characters", default=True, type=bool,
                        help="Whether to scrape the characters wiki page")
    parser.add_argument("--scrape-spreadsheet", default=True, type=bool,
                        help="Whether to scrape the Otzdarva spreadsheet")
    return parser.parse_args()


def save_json(file_name, content):
    current_date = datetime.now().strftime('%d-%m-%Y')

    with open(f'{util.one_dir_up()}/out/archive/{file_name}_{current_date}.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)

    with open(f'{util.one_dir_up()}/out/{file_name}_LATEST.json', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
