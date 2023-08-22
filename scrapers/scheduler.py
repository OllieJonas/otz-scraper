import json
import os
from datetime import datetime

import main as scraper
import cli
import util

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from scrapers import constants


def main():
    util.make_dirs()
    args = cli.parse_scheduler_args()

    credentials = Credentials.from_service_account_file(args.creds_path)
    service = build('sheets', 'v4', credentials=credentials)

    current_date = datetime.now()

    update_last_refresh, sheet_updated = requires_refresh(service, current_date, args.refresh_time) or args.force
    refresh = update_last_refresh or sheet_updated

    if args.force:
        print("Program has been forced to run!")
    else:
        print(f'Update{" " if refresh else " is not "}required! '
              f'{"Running" if refresh else "Exiting"} program ...')

    if refresh or args.force:
        scraper.scrape_all(args=args, current_date=current_date.strftime('%d-%m-%Y'), sheets_service=service)


def requires_refresh(service, current_date, refresh_rate_days):
    last_updated = {}
    path = f'{util.one_dir_up()}/out/last_updated_LATEST.json'
    datetime_format_str = "%d-%m-%Y"

    if not os.path.exists(path):
        print("last_updated_LATEST.json doesn't exist! Running program ...")
        return False

    with open(path) as f:
        last_updated = json.load(f)

    if 'application' not in last_updated or 'spreadsheet' not in last_updated:
        print("Malformed last_updated_LATEST.json file! Running program ...")
        return False

    last_update_app, last_update_spreadsheet = \
        datetime.strptime(last_updated['application'], datetime_format_str).date(), \
        datetime.strptime(last_updated['spreadsheet'], datetime_format_str).date()

    update_last_refresh = (current_date.date() - last_update_app).days >= refresh_rate_days
    sheet_updated = has_sheet_been_updated(service, last_update_spreadsheet)

    return update_last_refresh, sheet_updated


def has_sheet_been_updated(service, program_last_update,
                           last_update_cell=constants.KILLER_CONSTANTS['misc']['last_updated'],
                           spreadsheet_id=constants.OTZ_SPREADSHEET_ID):
    response = service.spreadsheets().get(spreadsheetId=spreadsheet_id, ranges=[last_update_cell], includeGridData=True
                                          ).execute()['sheets'][0]['data'][0]['rowData'][0]['values'][0]

    if not response['effectiveValue'] or not response['effectiveValue']['numberValue']:
        raise KeyError("[effectiveValue][numberValue] not in response! "
                       "(most likely because the last updated cell is incorrect! :/)")

    last_update_date = util.datetime_from_google_sheets(response['effectiveValue']['numberValue']).date()
    return last_update_date != program_last_update


if __name__ == "__main__":
    main()
