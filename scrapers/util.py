from __future__ import annotations

import json
import os
import re
from typing import ValuesView

import requests
from bs4 import BeautifulSoup


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


def replace_all_wiki_links(soup: BeautifulSoup,
                           wiki_base_link: str = "https://deadbydaylight.fandom.com/wiki/") -> BeautifulSoup:
    for a in soup.find_all('a'):
        a['href'] = a['href'].replace('/wiki/', wiki_base_link)

    return soup


def remove_excessive_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text)


def pretty_print(obj):
    print(json.dumps(obj, sort_keys=True, indent=4))


def one_dir_up():
    return os.path.abspath(os.path.join(__file__, '../..'))


def rgb_to_hex(red: float, green: float, blue: float) -> str:
    """ from here: https://stackoverflow.com/questions/214359/converting-hex-color-to-rgb-and-vice-versa """
    return '#%02x%02x%02x' % (round(red * 255), round(green * 255), round(blue * 255))
