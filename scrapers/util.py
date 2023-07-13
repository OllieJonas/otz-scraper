from __future__ import annotations

import json
import os
from typing import ValuesView

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


def flatten_list(lst: list | ValuesView) -> list:
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


def one_dir_up():
    return os.path.abspath(os.path.join(__file__, '../..'))
