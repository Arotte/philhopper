""" philhopper.py

    From any starter Wikipedia article, hop to the
    Philosophy article by following link `i` in the
    description of each article.

    Usage:
        python philhopper.py

    Tested with Python 3.10.7

    Author: Aron Molnar (gh/Arotte)
"""

import tqdm
import requests
import sys
import os
from urllib.parse import unquote
from bs4 import BeautifulSoup

from config import (
    WIKIPEDIA_API_BASE_URL,
    WIKIPEDIA_BASE_URL,
    MAX_HOPS,
    WIKI_URL_OF_PHILOSOPHY,
)

# full path of this script
SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))

# =============================================================================
# HELPERS
# =============================================================================


def check_url(url: str) -> str:
    """Check if url is full or partial"""

    if url.startswith("http"):
        return url
    else:
        return WIKIPEDIA_BASE_URL + url


def parenthetic_contents(string: str):
    """Generate parenthesized contents in string as pairs (level, contents)"""
    stack = []
    for i, c in enumerate(string):
        if c == "(":
            stack.append(i)
        elif c == ")" and stack:
            start = stack.pop()
            yield (len(stack), string[start + 1 : i])


def print_list_pretty(l: list):
    """Print list in a (semi-)pretty way"""

    for i in range(len(l)):
        print(f"{i+1}: {l[i]}")


def encode_fix(url: str) -> str:
    """Fix encoding of url"""

    # if url includes %, it is encoded
    if "%" in url:
        url = unquote(url)

    return url


# =============================================================================
# ARTICLE DATA OBJECT
# =============================================================================


class Page:
    def __init__(
        self,
        db_rowid,
        wiki_pageid,
        pagetitle,
        ithlink,
        i,
        fullurl,
        titleurl,
        parent_rowid,
    ):
        self.db_rowid = db_rowid
        self.wiki_pageid = wiki_pageid
        self.pagetitle = pagetitle
        self.ithlink = ithlink
        self.i = i
        self.fullurl = fullurl
        self.titleurl = titleurl
        self.parent_rowid = parent_rowid

    def to_tuple(self):
        return (
            self.db_rowid,
            self.wiki_pageid,
            self.pagetitle,
            self.ithlink,
            self.i,
            self.fullurl,
            self.titleurl,
            self.parent_rowid,
        )

    def tuple_without_rowid(self):
        return self.to_tuple()[1:]

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f"WikiPage(\n\tdb_rowid={self.db_rowid},\n\twiki_pageid={self.wiki_pageid},\n\tpagetitle={self.pagetitle},\n\tithlink={self.ithlink},\n\ti={self.i},\n\tfullurl={self.fullurl},\n\ttitleurl={self.titleurl},\n\tparent_rowid={self.parent_rowid}\n)"


# =============================================================================
# LINK EXTRACTION
# =============================================================================


def extract_link(page_url: str, link_i: int) -> tuple:
    """
    Extract i-th link from the description of a Wikipedia article

    page_url: url of the Wikipedia article
    i: the i-th link to extract
    """

    ### retrieve page html

    data = requests.get(page_url).text

    # check data
    if data is None:
        print(f"Extraction failed: no data (url: {page_url})")
        return (None, None, None)

    soup = BeautifulSoup(data, "html.parser")

    ### clean up the html

    # remove thumbnails
    for div in soup.find_all("div", {"class": "thumb"}):
        div.decompose()
    # remove sidebars
    for div in soup.find_all("table", {"class": "sidebar"}):
        div.decompose()
    # remove all tables
    for table in soup.find_all("table"):
        table.decompose()
    # remove notes at the top (class: hatnote)
    for div in soup.find_all("div", {"class": "hatnote"}):
        div.decompose()

    ### find paragraphs in html

    # find containers with classes specific classes
    containers = soup.find_all(
        "div", {"class": ["mw-parser-output", "mw-body-content", "vector-body"]}
    )

    if containers is None:
        print(f"Extraction failed: no containers")
        return (None, None, None)

    # list of paragraphs inside containers
    ps = []

    for container in containers:
        ps += container.find_all("p")

    links = []

    ### extract links from paragraphs

    # look in first x paragraphs
    max_paras = 3
    x = max_paras if len(ps) > max_paras else len(ps)

    for paragraph_n in range(0, x):
        # get contents of parentheses
        nested_paren_contents = list(parenthetic_contents(str(ps[paragraph_n])))
        strs_in_paren = [
            s[1] for s in nested_paren_contents
        ]  # get second element of each tuple (level, contents)

        # for all anchor tags inside the current paragraph
        for a in ps[paragraph_n].find_all("a"):
            if a.has_attr("href") and a["href"].startswith("/wiki/"):

                # check if the anchor tag is inside parentheses
                in_paren = False
                for para in strs_in_paren:
                    if str(a) in para:
                        in_paren = True
                        break

                if not in_paren:
                    links.append(a)

        if len(links) >= link_i:
            break

    ### if no links found, try a different strategy

    if len(links) == 0:
        # try another link searching strategy:
        # look for anchor tags that have an href attribute
        # starting with 'wiki/' and are not inside parentheses
        for a in soup.find_all("a"):
            if a.has_attr("href") and a["href"].startswith("/wiki/"):
                links.append(a)

        # check for parentheses
        nested_paren_contents = list(parenthetic_contents(str(soup)))
        strs_in_paren = [s[1] for s in nested_paren_contents]

        for a in links:
            in_para = False
            for para in strs_in_paren:
                if str(a) in para:
                    in_para = True
                    break

            if in_para:
                links.remove(a)

    ### return results

    # if we don't have the i-th link, return None
    if len(links) < link_i:
        return (None, None, None)

    link = links[link_i - 1]
    ret = (link["href"], link.text, link["title"])

    return ret


# =============================================================================
# GET RANDOM WIKI ARTICLES
# =============================================================================


def get_random_pages(n: int, link_i: int) -> list:
    print(f"\nGetting {n} random Wikipedia pages...")

    ### checks

    if n < 1 or n > 500:  # how many random pages to get
        raise ValueError("n must be between 1 and 500")

    if link_i < 1 or link_i > 300:  # get i-th link of each page
        raise ValueError("i must be between 1 and 300")

    ### get random pages via Wikipedia API

    PARAMS = {
        "action": "query",
        "format": "json",
        "list": "random",
        "rnlimit": str(n),
        "rnnamespace": "0",
    }
    S = requests.Session()
    R = S.get(url=WIKIPEDIA_API_BASE_URL, params=PARAMS)
    DATA = R.json()
    RANDOMS = DATA["query"]["random"]

    ### extract info from the pages

    print(f"Extracting data from {n} random Wikipedia pages")

    PAGES = []
    for r in tqdm.tqdm(RANDOMS):
        page_title = r["title"]
        page_id = r["id"]

        # get full url of each page

        PARAMS = {
            "action": "query",
            "format": "json",
            "prop": "info",
            "inprop": "url",
            "pageids": page_id,
        }

        S = requests.Session()
        R = S.get(url=WIKIPEDIA_API_BASE_URL, params=PARAMS)
        DATA = R.json()

        page_url = DATA["query"]["pages"][str(page_id)]["fullurl"]
        page_title_from_url = page_url.split("/")[-1]
        page_lang = DATA["query"]["pages"][str(page_id)]["pagelanguage"]

        if page_lang != "en":
            continue

        if page_url is None:
            continue

        PAGES.append(page_url)

    ### done

    return PAGES


# =============================================================================
# WIKI URL TO OBJECT
# =============================================================================


def url_to_page_obj(url: str, link_i: int) -> Page:

    ### url checks

    url = check_url(url)
    url = encode_fix(url)

    ### get info about article via Wikipedia API

    PARAMS = {
        "action": "query",
        "format": "json",
        "prop": "info",
        "inprop": "url",
        "titles": url.split("/")[-1],
    }
    S = requests.Session()
    R = S.get(url=WIKIPEDIA_API_BASE_URL, params=PARAMS)
    DATA = R.json()

    # check if page exists
    if "-1" in DATA["query"]["pages"]:
        print(f"Page does not exist ({url})")
        return None

    # extract info from returned json
    page_id = list(DATA["query"]["pages"].keys())[0]
    page_url = DATA["query"]["pages"][page_id]["fullurl"]
    page_title_from_url = page_url.split("/")[-1]
    page_lang = DATA["query"]["pages"][page_id]["pagelanguage"]

    # check if page is in English
    if page_lang != "en":
        print(f"Page is not in English ({url})")
        return None

    ### extract link from article

    extracted_link = None
    try:
        extracted_link = extract_link(page_url, link_i)
    except Exception as e:
        print(f"Error during link extraction: {e} ({url})")
        return None
    page_ithlink = extracted_link[0]  # get url only (url, text, title)

    if page_ithlink is None:
        print(f"No link found ({url})")
        return None

    ### done, construct Page object

    return Page(
        None,  # rowid is none as this page is not yet in the database
        page_id,
        page_title_from_url,
        page_ithlink,
        link_i,
        page_url,
        page_title_from_url,
        None,  # rowid of parent will be None as this is a leaf node (or we're not yet sure)
    )


# =============================================================================
# THE WIKI HOPPER
# =============================================================================


def hop_to_philosophy(start_url: str, link_i: int) -> list:

    # check and fix url
    start_url = encode_fix(start_url)

    # get first page
    start = url_to_page_obj(start_url, link_i)

    if start is None:
        print("Start page is not valid")
        return None

    # nice prints
    print()
    print(f"Hopping to Philosophy from '{start.pagetitle}'...")
    print(f"Max hops = {MAX_HOPS}, i = {link_i}")

    # initialize hop chain (list of Page objects)
    pages = [start]

    print(f"\t0. {start.pagetitle} ({start.fullurl})")

    # hop
    for hop_i in range(0, MAX_HOPS):

        # get next page
        next_page = url_to_page_obj(pages[-1].ithlink, link_i)

        # if next page is None, stop
        if next_page is None:
            print("Parsing error - hopping stopped")
            return None

        print(f"\t{hop_i + 1}. {next_page.pagetitle} ({next_page.fullurl})")

        # if next page is already in the list, we're in a cycle
        if next_page.wiki_pageid in [p.wiki_pageid for p in pages]:
            print("Cycle detected - hopping stopped")
            return None

        # philosophy reached
        if next_page.ithlink == WIKI_URL_OF_PHILOSOPHY:
            print("Reached Philosophy page - hopping stopped")
            break

        # add article to list
        pages.append(next_page)

    # done
    return pages


# =============================================================================
# SCRIPT RUNNER
# =============================================================================


def main():

    print(f"\nWARNING: This script will run forever, press Ctrl+C to stop\n")

    link_i = 1  # get i-th link of each page
    n = 10  # how many random pages to get in each iteration

    try:
        while True:  # infinite loop, break with Ctrl+C

            # randomize link i
            # link_i = random.randint(1, 3)

            # get n random articles
            random_articles = get_random_pages(n, link_i)

            # print random articles
            print()
            print("Random articles:")
            for article in random_articles:
                print(article)

            # hop to philosophy
            for article in random_articles:
                hop_to_philosophy(article, link_i)

    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    print(f"Running {__file__}...")

    main()
