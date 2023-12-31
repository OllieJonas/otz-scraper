import os
import threading
import json

from datetime import datetime
from typing import Dict

from unidecode import unidecode

import util
from scrapers import constants


def _build_survivor_json():
    return {
        "name": "",
        "icon": "",
        "image_half": "",
        "image_full": "",
        "wiki_link": "",
        "lore": "",
    }


def _build_killer_json():
    return {
        "name": "",
        "former_name": "",
        "height": "",
        "icon": "",
        "image_half": "",
        "image_full": "",
        "wiki_link": "",
        "power": {
            "name": "",
            "icon": "",
            "desc": "",
        },
        "lore": "",
    }


CHARACTERS_LATEST = None


def scrape_characters_mt(character_type: str, no_workers: int, force_refresh: bool = False) -> Dict:
    """
    Scrape perks, but using threads! Very simple threading here; work is allocated evenly and in-order
    (eg. [job 1, job 2, job 3], no_threads=3 -> thread 1 gets job 1, thread 2 gets job 2, thread 3 gets job 3.)

    Character scrapers (each individual wiki link) takes a while to run (and are very unlikely to change between
    each run), so it's probably a good idea to check if any have already been scraped, so we're not repeating ourselves.

    There is basically no thread safety here, but given that every worker should be doing separate characters &
    contributing to the list separately with no shared data, I don't think this is much of an issue.
    """
    if no_workers == 1:
        return scrape_characters(character_type)

    ct_caps = character_type.capitalize()

    print(f"Starting scraping Character Wiki for {ct_caps} (no-workers={no_workers})...")

    url = f"https://deadbydaylight.fandom.com/wiki/{ct_caps}"

    already_scraped_list, prev_characters = _generate_already_scraped_list(character_type, force_refresh)

    wiki_links = _scrape_wiki_links(url, ct_caps)
    wiki_links = [wl for wl in wiki_links if wl not in already_scraped_list]
    wiki_links = [(wl, i) for i, wl in enumerate(wiki_links)]

    if len(wiki_links) == 0:
        return {character_type: prev_characters}

    work_allocs = util.divide_list(wiki_links, min(no_workers, len(wiki_links)))

    characters = [None] * len(wiki_links)

    def worker_func(_work_alloc, _characters):
        for work in _work_alloc:
            ch_info = _scrape_character(work[0], character_type)
            characters[work[1]] = ch_info

    workers = [threading.Thread(target=worker_func, args=(work_alloc, characters)) for work_alloc in
               work_allocs]

    [worker.start() for worker in workers]
    [worker.join() for worker in workers]

    characters = {ch['name']: ch for ch in characters}

    # needs character_type: X to cross-reference old run
    return {character_type: prev_characters | characters}


def scrape_characters(character_type, force_refresh=False):
    already_scraped_list = _generate_already_scraped_list(character_type, force_refresh)

    url = f"https://deadbydaylight.fandom.com/wiki/{character_type}"

    print(f"Starting scraping Character Wiki for {character_type}...")

    wiki_links = _scrape_wiki_links(url, character_type)
    characters = [_scrape_character(wl, character_type) for i, wl in enumerate(wiki_links)]
    characters = {ch['name']: ch for ch in characters}

    return characters


def _scrape_wiki_links(url, character_type):
    soup = util.get_content(url)

    # finds the header tag for "List of X", then finds the next div beyond that.
    character_name_div = soup.find('span', id=f'List_of_{character_type}').find_all_next('div')[0]
    character_divs = character_name_div.find_all('div')
    character_divs = [cd for i, cd in enumerate(character_divs) if i % 3 == 0]
    wiki_links = [cd.find('a')['href'].replace('/wiki/', constants.DBD_WIKI_BASE_LINK) for cd in character_divs]
    return wiki_links


def _scrape_character(url, character_type):
    soup = util.get_content(url)
    is_killer = character_type == "Killers"

    info = _build_killer_json() if is_killer else _build_survivor_json()
    name, icon = _scrape_name_and_icon(soup)
    info['name'] = unidecode(name).replace("The ", "")
    info['icon'] = icon

    lore, image_full = _scrape_lore_and_image_full(soup)

    info['lore'] = lore
    info['image_full'] = image_full
    info['wiki_link'] = url

    info['image_half'] = util.strip_revision_from_url(soup.find('span', id='Overview').find_next('a')['href'])

    if is_killer:
        info = _scrape_killer(soup, info)

    return info


def _scrape_killer(soup, info):
    info_table = soup.find("table", class_="infoboxtable")
    info['former_name'] = info_table.find('td', class_="valueColumn").text.strip()
    info['height'] = info_table.find_all(lambda tag: tag.name == 'td' and tag.text.startswith("Height"))[0] \
        .find_all_next('td', class_='valueColumn')[0].text.strip()

    power = []
    power_curr = soup.find('span', id=lambda v: v is not None and v.startswith("Power:_")).find_parent()
    power_icon_found = False
    power_icon = ""
    info['power']['name'] = power_curr.text.split(": ")[1]

    while (power_curr := power_curr.find_next_sibling()).get('style') != "clear:both" and \
            power_curr.find('span', id='Power_Trivia') is None:

        if power_curr.find('a', class_="image") is not None and not power_icon_found:
            power_icon = power_curr.find('a')['href']
            power_icon_found = True
        elif power_curr.name == 'p':
            power.append(power_curr.text.strip())

    info['power']['icon'] = power_icon
    info['power']['desc'] = "\n".join(power)

    return info


def _scrape_name_and_icon(soup):
    info_table = soup.find("table", class_="infoboxtable")
    name = util.remove_excessive_whitespace(info_table.find('th', class_='center bold').text).strip()
    icon = util.strip_revision_from_url(
        info_table.find('th', class_="center charInfoboxImage").find('a')['href'].strip())
    return name, icon


def _scrape_lore_and_image_full(soup):
    lore_curr = soup.find('span', id='Lore').find_parent()

    lore = []
    image_full = ""

    while (lore_curr := lore_curr.find_next_sibling()).get('style') != "clear:both" and \
            lore_curr.find('span', id='Load-out') is None:

        if lore_curr.find('a', class_="image") is not None:
            image_full = util.strip_revision_from_url(lore_curr.find('a')['href'])
        elif lore_curr.name == 'p' and lore_curr.find('i') is not None:
            lore.append(lore_curr.find('i').text)

    return "\n".join(lore), image_full


def _generate_already_scraped_list(character_type, force_refresh: bool):
    global CHARACTERS_LATEST

    if force_refresh:
        return [], {}

    path = f'{util.one_dir_up()}/out/characters_LATEST.json'

    if not os.path.exists(path):
        return [], {}

    if CHARACTERS_LATEST is None:
        with open(path, encoding='utf-8') as f:
            CHARACTERS_LATEST = json.load(f)

    return [ch['wiki_link'] for ch in CHARACTERS_LATEST[character_type].values() if 'wiki_link' in ch], \
           CHARACTERS_LATEST[character_type]


if __name__ == "__main__":
    killer_characters = scrape_characters('Killers')
    survivor_characters = scrape_characters('Survivors')
    current_date = datetime.now().strftime('%d-%m-%Y')

    util.make_dirs()

    util.save_json("characters.json", killer_characters | survivor_characters, current_date)
