import util
from scrapers import constants


def _build_survivor_json():
    return {
        "name": "",
        "icon": "",
        "image_full": "",
        "lore": "",
    }


def _build_killer_json():
    return {
        "killer_name": "",
        "former_name": "",
        "icon": "",
        "image_full": "",
        "lore": "",
        "height": "",
        "power": {
            "name": "",
            "icon": "",
            "desc": "",
        },
    }


def scrape_characters(character_type):
    url = f"https://deadbydaylight.fandom.com/wiki/{character_type}"

    wiki_links = _scrape_wiki_links(url, character_type)
    return [_scrape_character(url, character_type) for url in wiki_links]


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
    if character_type == "Survivors":
        return _scrape_killer(soup)
    else:
        return _scrape_survivor(soup)


def _scrape_survivor(soup):
    return None


def _scrape_killer(soup):
    return None
