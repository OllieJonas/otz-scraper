import argparse
import util


def main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=None)
    parser.add_argument("--creds_path",
                        default=f"{util.one_dir_up()}/credentials.json",
                        type=str,
                        help='service account credentials path (for google sheets API)')

    # The Google Sheets API has a rate limit of 60 reqs/min per user. Unfortunately, we don't necessarily know how many
    # characters there are on the sheet. At time of writing (10/7/23), there are 32 killers and 38 survivors.
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

    # ---------------- OTZ SCRAPER ARGS --------------------
    parser.add_argument("--min-characters", default=32, type=int,
                        help='the minimum amount of characters to search for on the Otz spreadsheet.')
    parser.add_argument("--min-universals", default=12, type=int,
                        help='the minimum amount of universal (base) perks to search for on the Otz spreadsheet.')

    # ---------------- CHARACTER SCRAPER ARGS --------------------
    parser.add_argument("--no-workers", default=16, type=int,
                        help='number of workers to use for character scraper. '
                             'recommended amount is the number of cores you have (including hyper-threading); '
                             'any more may cause slowdown!')

    # ---------------- SCRAPE ARGS --------------------
    parser.add_argument("--ignore-prepare-final-json", action="store_true",
                        help="Whether to collate information from characters, perks and spreadsheet to create a final"
                             "JSON file for front-end usage.")
    parser.add_argument("--ignore-perk-scraper", action="store_true",
                        help="Whether to scrape the perks wiki page")
    parser.add_argument("--ignore-character-scraper", action="store_true",
                        help="Whether to scrape the characters wiki page")
    parser.add_argument("--ignore-sheet-scraper", action="store_true",
                        help="Whether to scrape the Otzdarva spreadsheet")

    return parser


def scheduler_parser():
    parser_ = main_parser()
    # ---------------- MAIN ARGS --------------------
    parser_.add_argument("--force", action="store_true",
                         help="Whether to force the application to refresh the JSON files "
                              "(it won't update if the 'Last Updated' text on the sheet is the same as the last run).")

    # Otzdarva doesn't necessarily update the "Last Updated" value in the Spreadsheet
    parser_.add_argument("--refresh-time", default=3, type=int,
                         help="The minimum time that has to have elapsed since the last run of this program, in days.")

    return parser_


def parse_main_args():
    parser_ = main_parser()
    return parser_.parse_args()


def parse_scheduler_args():
    parser_ = scheduler_parser()
    return parser_.parse_args()
