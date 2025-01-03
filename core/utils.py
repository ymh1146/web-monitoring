from urllib.parse import urlparse


def norm_url(url):
    parsed = urlparse(url)
    return f"{parsed.netloc}{parsed.path}"
