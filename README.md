# otz-scraper

Simple scraper for the Otzdarva Killer and Survivor Info spreadsheet for Dead by Daylight (DBD). 

More specifically, this scrapes three "types" of sites: Characters ([Example](https://deadbydaylight.fandom.com/wiki/Evan_MacMillan)), Perks ([Example](https://deadbydaylight.fandom.com/wiki/Survivor_Perks)), and the Otzdarva Quick Info for DBD Spreadsheet ([Here](https://otzdarva.com/spreadsheet)). For an example of what the output of each of these scrapers does, please refer to ```out/characters_LATEST.json```, ```out/perks_LATEST.json```, and ```out/spreadsheet_LATEST.json``` respectively.

This program is primarily made for preparing a JSON file to use for the front-end of the website version of the Killer and Survivor Info parts for DBD ([Website](https://olliejonas.github.io/otz-sheet), [Source Code](https://github.com/OllieJonas/otz-sheet)), although each scraper is able to act independently. 

## Requirements
- [Requests](https://pypi.org/project/requests/)
- [BeautifulSoup](https://pypi.org/project/beautifulsoup4/)
- [Levenshtein](https://pypi.org/project/Levenshtein/)
- [Google API Python Client](https://pypi.org/project/google-api-python-client/)
- [Unidecode](https://pypi.org/project/Unidecode/)

## Installation

1. Clone repo
2. Install requirements (also found in requirements.txt)
3. Place credentials.json for the Google Sheets API in root directory of project (for more information on this, there's a guide [here](https://medium.com/@a.marenkov/how-to-get-credentials-for-google-sheets-456b7e88c430) on how to obtain these)
4. Run ```main.py``` in scrapers
 
## Program Arguments
- __min-characters:__ The minimum number of characters to search for on the Otz spreadsheet (defaults to 32, the total number of Killers). Any beyond this should be found, but this number should be as high as possible to reduce calls to the Sheets API.
- __min-universals:__ The minimum number of base perks to search for on the Otz spreadsheet (defaults to 12, the minimum amount of base perks between Survivors and Killers).
- __no-workers:__ The number of workers to use for the character scraper. This should be no higher than the number of cores you have on your computer (including hyper-threading).
- __prepare-final-json:__ Whether to prepare the final JSON file for the website (defaults to True). If this is set to True, then the below three arguments will also default to True (all three are needed for the final JSON)
- __scrape-perks:__ Whether to scrape the DBD perk wiki (default to True).
- __scrape-characters:__ Whether to scrape characters from the DBD wiki (default to True).
- __scrape-spreadsheet:__ Whether to scrape the Otzdarva spreadsheet (default to True).
