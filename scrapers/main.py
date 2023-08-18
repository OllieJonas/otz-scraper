import argparse

import scrape
from scrapers import util


def main():
    util.make_dirs()
    args = parse_args()

    scrape.scrape_all(args)


def parse_args() -> argparse.Namespace:
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


if __name__ == "__main__":
    main()
