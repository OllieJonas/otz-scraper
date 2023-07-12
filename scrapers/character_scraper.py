import requests
from bs4 import BeautifulSoup


def _build_character_json():
    return {
        ""
    }


def scrape_characters(url):
    character_names = _scrape_character_names(url)


def _scrape_character_names(url):
    soup = BeautifulSoup(url, 'html.parser')
    return None
