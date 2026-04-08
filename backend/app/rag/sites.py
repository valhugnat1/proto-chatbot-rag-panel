"""Dynamic configuration and filtering defaults for the scraper."""
from dataclasses import dataclass
from urllib.parse import urlparse

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}

# Unified exclusion list (common web noise + Wikipedia specific)
EXCLUDED_PREFIXES = (
    "/login", "/signin", "/search", "/contact", "/legal", "/sitemap",
    "/cart", "/checkout", "/wp-admin", "/wp-login",
    "/wiki/Spécial:", "/wiki/Special:", "/wiki/Aide:", "/wiki/Help:",
    "/wiki/Discussion", "/wiki/Talk:", "/wiki/Wikipédia:", "/wiki/Wikipedia:",
    "/wiki/Utilisateur:", "/wiki/User:", "/wiki/Fichier:", "/wiki/File:",
    "/wiki/Catégorie:", "/wiki/Category:", "/wiki/Portail:", "/wiki/Portal:",
    "/wiki/Modèle:", "/wiki/Template:", "/wiki/MediaWiki:", "/w/"
)

EXCLUDED_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".mp4", ".mp3", ".zip", ".gz", ".tar", ".css", ".js", ".ico",
    ".xml", ".rss", ".woff", ".woff2", ".ttf", ".eot",
)

@dataclass
class SiteConfig:
    """Dynamic configuration for a single scrape target."""
    seed_url: str
    max_depth: int = 2
    max_pages: int = 20
    politeness_delay: float = 0.5
    min_content_chars: int = 200
    user_agent: str = DEFAULT_USER_AGENT

    @property
    def domain(self) -> str:
        return urlparse(self.seed_url).netloc

    def build_headers(self) -> dict[str, str]:
        headers = {"User-Agent": self.user_agent}
        headers.update(DEFAULT_HEADERS)
        return headers