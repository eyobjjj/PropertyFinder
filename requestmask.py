import logging
from fake_useragent import UserAgent
from settings import SCRAPER_API_KEY, USE_SCRAPER_API

ua = UserAgent()


def get_random_user_agent():
    """Return a random User-Agent string."""
    try:
        return ua.random
    except Exception as e:
        logging.warning(f"Failed to get random User-Agent: {e}")
        # fallback to a simple, common user agent
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
               "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

def get_random_headers(extra_headers: dict = None) -> dict:
    """Generate headers for HTTP request with optional override."""
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache"
    }

    if extra_headers:
        headers.update(extra_headers)
    return headers


def build_url(original_url: str) -> str:
    """
    Build the final URL to be used for scraping.
    """
    if USE_SCRAPER_API:
        return f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={original_url}"
    return original_url


