from __future__ import annotations

import json
import os
import re
import typing
from typing import ValuesView, Dict, Hashable

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
                    self._set_inverse(key, v)
            else:
                self._set_inverse(key, value)

    def _set_inverse(self, key, value):
        if value in self.inverse:
            self.inverse[value] = [self.inverse[value], key]
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


def rgb_dict_to_dict(rgb: dict) -> Dict:
    return rgb_to_dict(rgb.get('red', 0.0), rgb.get('green', 0.0), rgb.get('blue', 0.0))


def rgb_to_dict(red: float, green: float, blue: float) -> Dict:
    return {
        "red": round(red * 255),
        "green": round(green * 255),
        "blue": round(blue * 255)
    }


def divide_list(input_list, N):
    avg = len(input_list) // N
    remainder = len(input_list) % N

    return [input_list[i * avg + min(i, remainder):(i + 1) * avg + min(i + 1, remainder)]
            for i in range(N)]


def strip_revision_from_url(url: str) -> str:
    return url.split(".png")[0] + ".png"


def update_key(d: Dict, old: Hashable, new: Hashable) -> Dict:
    if old == new:
        return d

    d[new] = d[old]
    del d[old]
    return d


if __name__ == "__main__":
    bi_dict = BiDict({
        "A": 1,
        "B": 2,
        "C": 1
    })
    print(bi_dict.inverse)
