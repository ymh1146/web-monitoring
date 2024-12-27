import requests
from config.settings import CDN_ERR_KEYS
from config.website_manager import load_sites
from core.database import save_status
from utils.logger import log_msg


def check_site_status(url):

    try:
        resp = requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        if any(err in resp.text for err in CDN_ERR_KEYS):
            return "CDN Error Page"
        elif resp.status_code == 200:
            return "OK"
        else:
            return f"Error: {resp.status_code}"
    except requests.exceptions.Timeout:
        return "连接超时"
    except requests.exceptions.RequestException as e:
        return str(e)


def record_status():

    sites = load_sites()
    for url in sites:
        status = check_site_status(url)
        save_status(url, status)
        if status != "OK":
            log_msg(f"网站 {url} 状态异常: {status}")

    log_msg("完成一次状态检查")
