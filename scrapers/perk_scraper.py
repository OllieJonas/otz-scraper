from datetime import datetime

import util
from unidecode import unidecode

KILLER_PERKS_URL = "https://deadbydaylight.fandom.com/wiki/Killer_Perks"
SURVIVOR_PERKS_URL = "https://deadbydaylight.fandom.com/wiki/Survivor_Perks"


def _build_perk_json() -> dict:
    return {
        "name": "",
        "icon": "",
        "description": "",
        "is_upcoming_patch": False
    }


def _get_url(character_type):
    return SURVIVOR_PERKS_URL if character_type == "Survivors" else KILLER_PERKS_URL


def scrape_perks(character_type: str, remove_desc_html: bool = False, remove_mini_perk_icons: bool = True) -> dict:
    """
    Scrape perk information from DBD perk table wiki pages. Works for all characters (i.e. both Killers and Survivors).

    Uses BeautifulSoup, so no "real" rate limits here.

    :param character_type: Either "Killers" or "Survivors"
    :param remove_desc_html: Whether to remove any in-line HTML in the perk description.
    :param remove_mini_perk_icons: Whether to remove the mini icons in perk descriptions (e.g., A Nurse's Calling has
                                   a mini icon after 'Auras' in its description on the wiki).

    :return: A dictionary of perks in the following format:
    {
        <character_name (/ "All")> (str)>: {
            <perk_name> (str): {
                icon (str):
                description (str):
                is_upcoming_patch (bool):
                patch_ver (only if is_up_coming_patch is True) (str):
            }
        }
    }
    """
    print(f"Starting scraping Wiki ({character_type}) for Perks...")

    url = _get_url(character_type)
    soup = util.get_content(character_type)

    perks = {}

    # only one table on the page, so we don't need to bother doing anything more rigorous
    table = soup.find('table')

    for i, row in enumerate(table.find_all('tr')[1:]):  # [1:] to remove header
        perk = _build_perk_json()  # keeps key ordering when inserting keys (I'm picky about this stuff okay :( )

        headers = row.find_all('th')

        icon = util.strip_revision_from_url(headers[0].find('a')['href'])
        perk_name = headers[1].text.strip()
        character_name = unidecode(headers[2].text.replace('.', '').strip())  # 'All' has a '.' in front of it

        description = row.find('td').find('div', class_='formattedPerkDesc')
        description = util.replace_all_wiki_links(description)

        upcoming_patch = description.find("div", class_="dynamicTitle")

        if remove_mini_perk_icons and description.span is not None:
            spans = soup.find_all(lambda tag: tag.name == 'span' and 'style' in tag.attrs and 'padding' in tag['style'])
            for span in spans:
                if span:
                    span.replace_with('')
                    span.extract()

        if remove_desc_html:
            description = description.text
        else:
            description = description.prettify()

        if upcoming_patch:
            patch_split = upcoming_patch.text.split(":")  # quite dodgy; should probably be using regex but here we are
            patch_ver = patch_split[1].strip()
            perk['patch_ver'] = patch_ver

            if remove_desc_html:  # need to add a \n between the patch ver and perk desc when removing the HTML content.
                patch_idx = description.find(patch_ver) + len(patch_ver)
                description = description[:patch_idx] + "\n" + description[patch_idx:]

        # create perk dict
        perk['icon'] = icon
        perk['description'] = description
        perk['is_upcoming_patch'] = upcoming_patch is not None

        # some really annoying hard-coded cases where it differs from the spreadsheet and the wiki
        # changing the perk names on the scraper to the spreadsheet, purely because it's much easier to follow in the
        # code (should probably be the other way around but oh well)

        # otz doesn't include scourge hook in perk names
        perk_name = perk_name.replace("Scourge Hook: ", "").strip()
        perk['name'] = perk_name

        if character_name not in perks:
            perks[character_name] = {}

        perks[character_name][perk_name] = perk
    return perks


if __name__ == "__main__":
    killer_characters = scrape_perks('Killers')
    survivor_characters = scrape_perks('Survivors')
    current_date = datetime.now().strftime('%d-%m-%Y')

    util.make_dirs()

    util.save_json("characters.json", killer_characters | survivor_characters, current_date)
