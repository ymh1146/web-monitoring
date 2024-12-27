import json
import os
from config.settings import DATA_DIR

CFG_FILE = os.path.join(DATA_DIR, "sites.json")


def load_sites():

    try:
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_sites(sites):

    valid_sites = []
    for site in sites:
        if site.strip():
            if not site.startswith(("http://", "https://")):
                site = "https://" + site
            valid_sites.append(site)

    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(valid_sites, f, ensure_ascii=False, indent=4)

    return valid_sites


def norm_url(url):

    url = url.strip().lower()
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]
    return url.rstrip("/")
