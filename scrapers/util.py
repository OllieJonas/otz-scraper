import json

import requests
from bs4 import BeautifulSoup

DBD_WIKI_BASE_LINK = 'https://deadbydalight.fandom.com/wiki/'


class BiDict(dict):
    """
    Simple bi-directional dictionary.
    """

    def __init__(self, *args, **kwargs):
        super(BiDict, self).__init__(*args, **kwargs)

        self.inverse = {}

        for key, value in self.items():
            if isinstance(value, list):
                for v in value:
                    self.inverse[v] = key
            else:
                self.inverse[value] = key

    def __setitem__(self, key, value):
        if key in self:
            self.inverse[self[key]].remove(key)

        super(BiDict, self).__setitem__(key, value)
        self.inverse[value] = key

    def __delitem__(self, key):
        if self[key] in self.inverse and not self.inverse[self[key]]:
            del self.inverse[self[key]]
        super(BiDict, self).__delitem__(key)


def flatten_list(lst: list) -> list:
    return [item for sublist in lst for item in (sublist if isinstance(sublist, list) else [sublist])]


def get_content(url: str) -> BeautifulSoup:
    req = requests.get(url)
    return BeautifulSoup(req.content, 'html.parser')


def replace_all_wiki_links(soup: BeautifulSoup, wiki_base_link: str = DBD_WIKI_BASE_LINK) -> BeautifulSoup:
    for a in soup.find_all('a'):
        a['href'] = a['href'].replace('/wiki/', wiki_base_link)

    return soup


def pretty_print(obj):
    print(json.dumps(obj, sort_keys=True, indent=4))


def shape(arr):
    rows = len(arr)
    cols = len(arr[0]) if rows > 0 else 0
    return rows, cols


def simplify_sheets_request(ranges):
    ranges = sorted(set(ranges))
    print(f"r: {ranges}")
    prev_col, prev_row = -1, -1

    curr_range = []

    for cell in ranges:
        col, row = cell.col, cell.row
        prev_col = col
        prev_row = row

    return None


def strip_mini_icons(soup):
    pass
