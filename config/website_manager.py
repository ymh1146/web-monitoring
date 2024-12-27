import json
import os
from config.settings import DATA_DIR

CFG_FILE = os.path.join(DATA_DIR, "sites.json")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def load_sites():
    """加载网站配置"""
    try:
        with open(CFG_FILE, "r", encoding="utf-8") as f:
            sites = json.load(f)
            # 兼容旧格式
            if sites and isinstance(sites[0], str):
                sites = [{"url": url, "note": "", "request_body": "", "request_headers": DEFAULT_HEADERS} for url in sites]
            # 确保所有站点都有请求头
            for site in sites:
                if "request_headers" not in site:
                    site["request_headers"] = DEFAULT_HEADERS
            return sites
    except:
        return []


def save_sites(sites):
    """保存网站配置"""
    valid_sites = []
    for site in sites:
        if isinstance(site, str):
            site = {
                "url": site, 
                "note": "", 
                "request_body": "",
                "request_headers": DEFAULT_HEADERS
            }
            
        url = site["url"].strip()
        if url:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            valid_site = {
                "url": url,
                "note": site.get("note", "").strip(),
                "request_body": site.get("request_body", "").strip(),
                "request_headers": site.get("request_headers", DEFAULT_HEADERS)
            }
            valid_sites.append(valid_site)

    with open(CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(valid_sites, f, ensure_ascii=False, indent=4)

    return valid_sites


def norm_url(url):
    """标准化URL格式"""
    url = url.strip().lower()
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]
    return url.rstrip("/")
