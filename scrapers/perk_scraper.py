import util


def _build_perk_json() -> dict:
    return {
        "icon": "",
        "description": "",
        "is_upcoming_patch": False
    }


def scrape_perks(url: str, remove_desc_html: bool = True, remove_mini_perk_icons: bool = False) -> dict:
    """
    Scrape perk information from DBD perk table wiki pages. Works for all characters (i.e. both Killers and Survivors).

    Uses BeautifulSoup, so no "real" rate limits here.

    :param url: URL for DBD Wiki Page perk table.
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
    soup = util.get_content(url)

    perks = {}

    # only one table on the page, so we don't need to bother doing anything more rigorous
    table = soup.find('table')

    for i, row in enumerate(table.find_all('tr')[1:]):  # [1:] to remove header
        perk = _build_perk_json()  # keeps key ordering when inserting keys (I'm picky about this stuff okay :( )

        headers = row.find_all('th')

        icon = headers[0].find('a')['href']
        perk_name = headers[1].text.strip()
        character_name = headers[2].text.replace('.', '').strip()  # idk why but 'All' has a '.' in front of it

        description = row.find('td').find('div', class_='formattedPerkDesc')
        description = util.replace_all_wiki_links(description)

        upcoming_patch = description.find("div", class_="dynamicTitle")

        if remove_mini_perk_icons and description.span is not None:
            description.span.decompose()

        if remove_desc_html:
            description = description.text

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

        if character_name not in perks:
            perks[character_name] = {}

        perks[character_name][perk_name] = perk

    return perks
