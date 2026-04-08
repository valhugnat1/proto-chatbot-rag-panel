"""Site profiles for the scraper.

Each profile bundles together everything that's specific to one website:
- seed URL and allowed domain
- crawl tuning (depth, page cap, delay)
- HTTP headers (User-Agent in particular)
- URL filters (path prefixes and extensions to skip)

To add a new site, just append a `SiteConfig` to `SITES` below. Then run:

    python -m app.rag.ingest scrape --site <site_name>
    python -m app.rag.ingest all --site <site_name>

CLI flags (--max-pages, --max-depth, --delay, --user-agent, --seed-url) can
override any field of the profile at runtime.

# Note on protected sites

Most BNP-owned domains (group.bnpparibas, mabanque.bnpparibas, hellobank.fr)
are protected by Akamai/Cloudflare and return 403 to any non-browser client,
even with a realistic Chrome User-Agent. They detect us via JS challenge,
TLS fingerprinting, and behavioral signals. Bypassing this requires a real
headless browser (Playwright, Selenium) — out of scope for this POC.

Workaround: we use **Wikipedia** as the primary source. It has rich, accurate
articles on BNP Paribas and its subsidiaries, no anti-bot protection, and
trafilatura extracts the main text cleanly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urlparse


# --- Browser-like default headers --------------------------------------------
# Most corporate sites (Cloudflare, Akamai) reject obviously non-browser UAs
# with HTTP 403. We default to a realistic Chrome UA + common Accept headers.

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

# Path prefixes that almost never contain useful content
COMMON_EXCLUDED_PREFIXES = (
    "/login",
    "/signin",
    "/sign-in",
    "/search",
    "/contact",
    "/legal",
    "/sitemap",
    "/cart",
    "/checkout",
    "/wp-admin",
    "/wp-login",
)

# Wikipedia-specific noise: meta-pages, talk pages, special pages, help, user
# pages, file uploads. Apply to both fr.wikipedia.org and en.wikipedia.org.
WIKIPEDIA_EXCLUDED_PREFIXES = (
    "/wiki/Spécial:",
    "/wiki/Sp%C3%A9cial:",         # URL-encoded
    "/wiki/Special:",
    "/wiki/Aide:",
    "/wiki/Help:",
    "/wiki/Discussion:",
    "/wiki/Discussion_",
    "/wiki/Talk:",
    "/wiki/Wikipédia:",
    "/wiki/Wikip%C3%A9dia:",       # URL-encoded
    "/wiki/Wikipedia:",
    "/wiki/Utilisateur:",
    "/wiki/User:",
    "/wiki/Fichier:",
    "/wiki/File:",
    "/wiki/Catégorie:",
    "/wiki/Cat%C3%A9gorie:",
    "/wiki/Category:",
    "/wiki/Portail:",
    "/wiki/Portal:",
    "/wiki/Modèle:",
    "/wiki/Mod%C3%A8le:",
    "/wiki/Template:",
    "/wiki/MediaWiki:",
    "/w/",                          # /w/index.php?... edit links etc.
)

# File extensions that are not HTML
COMMON_EXCLUDED_EXTENSIONS = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".mp4", ".mp3", ".zip", ".gz", ".tar", ".css", ".js", ".ico",
    ".xml", ".rss", ".woff", ".woff2", ".ttf", ".eot",
)


@dataclass
class SiteConfig:
    """Configuration for one scrape target."""

    name: str
    seed_url: str
    # If None, derived from seed_url's netloc.
    allowed_domain: str | None = None
    max_depth: int = 3
    max_pages: int = 400
    politeness_delay: float = 0.75
    min_content_chars: int = 200
    user_agent: str = DEFAULT_USER_AGENT
    extra_headers: dict[str, str] = field(default_factory=dict)
    excluded_path_prefixes: tuple[str, ...] = COMMON_EXCLUDED_PREFIXES
    excluded_extensions: tuple[str, ...] = COMMON_EXCLUDED_EXTENSIONS
    # If True, ignore robots.txt entirely (use sparingly, only for sites you
    # control or where robots.txt is broken / overly restrictive for testing).
    ignore_robots: bool = False

    @property
    def domain(self) -> str:
        return self.allowed_domain or urlparse(self.seed_url).netloc

    def build_headers(self) -> dict[str, str]:
        """Build the full set of HTTP headers for this site."""
        headers = {"User-Agent": self.user_agent}
        headers.update(DEFAULT_HEADERS)
        headers.update(self.extra_headers)
        return headers


# ---------------------------------------------------------------------------
# Registered site profiles
# ---------------------------------------------------------------------------

# Combined Wikipedia exclusions (common + wiki-specific)
_WIKI_EXCLUSIONS = COMMON_EXCLUDED_PREFIXES + WIKIPEDIA_EXCLUDED_PREFIXES

SITES: dict[str, SiteConfig] = {

    # ─── Protected BNP-owned sites (will likely 403) ────────────────────────
    # Kept for reference / for the day they relax their bot protection, or if
    # you have a residential IP that gets through.

    "bnp-group": SiteConfig(
        name="bnp-group",
        seed_url="https://group.bnpparibas/",
        max_depth=3,
        max_pages=400,
        politeness_delay=0.75,
    ),

    "hellobank": SiteConfig(
        name="hellobank",
        seed_url="https://www.hellobank.fr/",
        max_depth=3,
        max_pages=200,
        politeness_delay=0.75,
    ),

    "mabanque": SiteConfig(
        name="mabanque",
        seed_url="https://mabanque.bnpparibas/",
        max_depth=3,
        max_pages=300,
        politeness_delay=0.75,
    ),

    # ─── Wikipedia profiles (reliable, no anti-bot) ─────────────────────────
    # These are the recommended sources for the demo. Wikipedia has high-quality
    # articles on BNP Paribas, its subsidiaries, and its history.

    # Main French Wikipedia article on BNP Paribas + linked banking topics.
    "wikipedia-bnp-fr": SiteConfig(
        name="wikipedia-bnp-fr",
        seed_url="https://fr.wikipedia.org/wiki/BNP_Paribas",
        max_depth=2,
        max_pages=40,
        politeness_delay=0.4,
        excluded_path_prefixes=_WIKI_EXCLUSIONS,
    ),

    # English Wikipedia article — usually more detailed on financials.
    "wikipedia-bnp-en": SiteConfig(
        name="wikipedia-bnp-en",
        seed_url="https://en.wikipedia.org/wiki/BNP_Paribas",
        max_depth=2,
        max_pages=40,
        politeness_delay=0.4,
        excluded_path_prefixes=_WIKI_EXCLUSIONS,
    ),

    # Hello bank! (BNP's online-only subsidiary) — Wikipedia article.
    "wikipedia-hellobank": SiteConfig(
        name="wikipedia-hellobank",
        seed_url="https://fr.wikipedia.org/wiki/Hello_bank!",
        max_depth=2,
        max_pages=20,
        politeness_delay=0.4,
        excluded_path_prefixes=_WIKI_EXCLUSIONS,
    ),

    # BNP Paribas Fortis (Belgian subsidiary).
    "wikipedia-fortis": SiteConfig(
        name="wikipedia-fortis",
        seed_url="https://fr.wikipedia.org/wiki/BNP_Paribas_Fortis",
        max_depth=2,
        max_pages=20,
        politeness_delay=0.4,
        excluded_path_prefixes=_WIKI_EXCLUSIONS,
    ),

    # Cetelem (BNP's consumer credit subsidiary).
    "wikipedia-cetelem": SiteConfig(
        name="wikipedia-cetelem",
        seed_url="https://fr.wikipedia.org/wiki/Cetelem",
        max_depth=2,
        max_pages=20,
        politeness_delay=0.4,
        excluded_path_prefixes=_WIKI_EXCLUSIONS,
    ),

    # ─── Generic / fallback ─────────────────────────────────────────────────

    # Old name kept as alias for backwards compat — same as wikipedia-bnp-fr.
    "wikipedia-bnp": SiteConfig(
        name="wikipedia-bnp",
        seed_url="https://fr.wikipedia.org/wiki/BNP_Paribas",
        max_depth=1,
        max_pages=20,
        politeness_delay=0.3,
        excluded_path_prefixes=_WIKI_EXCLUSIONS,
    ),
}


def get_site(name: str) -> SiteConfig:
    """Look up a site by name. Raises KeyError with a helpful message."""
    if name not in SITES:
        available = ", ".join(sorted(SITES.keys()))
        raise KeyError(
            f"Unknown site profile '{name}'. Available profiles: {available}"
        )
    return SITES[name]


def list_sites() -> list[str]:
    return sorted(SITES.keys())