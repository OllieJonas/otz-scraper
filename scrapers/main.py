import argparse
import json
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import util

from otz_scraper import scrape_otz
from perk_scraper import scrape_perks
from character_scraper import scrape_characters

KILLER_PERKS_URL = "https://deadbydaylight.fandom.com/wiki/Killer_Perks"
SURVIVOR_PERKS_URL = "https://deadbydaylight.fandom.com/wiki/Survivor_Perks"

# for Lore, Killer Power, etc.
KILLER_CHARACTERS_URL = "https://deadbydaylight.fandom.com/wiki/Killers"
SURVIVOR_CHARACTERS_URL = "https://deadbydaylight.fandom.com/wiki/Survivors"

OTZ_SPREADSHEET_ID = "1uk0OnioNZgLly_Y9pZ1o0p3qYS9-mpknkv3DlkXAxGA"
TEST_SPREADSHEET_ID = "1aNc3RqnjkAkxYX2msRzHahFVszkvCJl5PpR4ept7lpI"


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

    # killer_perks = scrape_perks(KILLER_PERKS_URL)
    # survivor_perks = scrape_perks(SURVIVOR_PERKS_URL)

    killer_characters = scrape_characters("Killers")
    survivor_characters = scrape_characters("Survivors")

    # credentials = Credentials.from_service_account_file(args.creds_path)
    # service = build('sheets', 'v4', credentials=credentials)
    #
    # killer_spreadsheet_info = scrape_otz(service, OTZ_SPREADSHEET_ID, 'killer',
    #                                      args.min_characters, args.min_universals)
    #
    # survivor_spreadsheet_info = scrape_otz(service, OTZ_SPREADSHEET_ID, 'survivor',
    #                                        args.min_characters, args.min_universals)
    #
    # save_json("killer_perks.json", killer_perks)
    # save_json("survivor_perks.json", survivor_perks)
    #
    # save_json("killer_spreadsheet.json", killer_spreadsheet_info)
    # save_json("survivor_spreadsheet.json", survivor_spreadsheet_info)


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
    return parser.parse_args()


def save_json(file_name, content):
    with open(f'{util.one_dir_up()}/out/{file_name}', 'w', encoding='utf-8') as f:
        json.dump(content, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
