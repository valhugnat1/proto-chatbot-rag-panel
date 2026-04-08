"""Generic BFS web crawler."""
import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import trafilatura
from bs4 import BeautifulSoup

from app.rag.sites import SiteConfig, EXCLUDED_PREFIXES, EXCLUDED_EXTENSIONS

logger = logging.getLogger(__name__)

@dataclass
class ScrapedPage:
    url: str
    title: str
    depth: int
    content: str
    scraped_at: str

def _normalize_url(base: str, link: str) -> str | None:
    if not link:
        return None
    absolute, _ = urldefrag(urljoin(base, link))
    return absolute

def _is_allowed(url: str, site: SiteConfig) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    
    if parsed.netloc != site.domain and not parsed.netloc.endswith("." + site.domain):
        return False
        
    path_lower = parsed.path.lower()
    if any(path_lower.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
        return False
    if any(path_lower.startswith(prefix.lower()) for prefix in EXCLUDED_PREFIXES):
        return False
        
    return True

def _load_robots(site: SiteConfig) -> RobotFileParser:
    rp = RobotFileParser()
    robots_url = f"https://{site.domain}/robots.txt"
    try:
        with httpx.Client(headers=site.build_headers(), timeout=10.0, follow_redirects=True) as client:
            resp = client.get(robots_url)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
                return rp
    except Exception as exc:
        logger.warning(f"Failed to load robots.txt: {exc} — assuming allow-all")
        
    rp.parse(["User-agent: *", "Disallow:"])
    return rp

async def crawl(site: SiteConfig) -> list[ScrapedPage]:
    """Run a depth-limited BFS crawl over the seed URL."""
    rp = _load_robots(site)
    headers = site.build_headers()
    
    visited = set()
    pages = []
    queue = deque([(site.seed_url, 0)])

    async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
        while queue and len(pages) < site.max_pages:
            url, depth = queue.popleft()
            
            if url in visited or depth > site.max_depth or not _is_allowed(url, site):
                continue
            visited.add(url)

            if not rp.can_fetch(headers["User-Agent"], url):
                continue

            try:
                response = await client.get(url)
            except Exception as exc:
                logger.warning(f"Fetch failed for {url}: {exc}")
                continue

            if response.status_code != 200 or "text/html" not in response.headers.get("content-type", ""):
                continue

            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            
            for time_tag in soup.find_all("time"):
                text = time_tag.get_text(strip=True)
                datetime_val = time_tag.get("datetime")
                
                if datetime_val and text:
                    time_tag.replace_with(f"{text} ({datetime_val})")
                elif text:
                    time_tag.replace_with(text)
                elif datetime_val:
                    time_tag.replace_with(datetime_val)

            clean_html = str(soup)
            content = (trafilatura.extract(clean_html, include_comments=False, include_tables=False) or "").strip()
            
            if len(content) >= site.min_content_chars:
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                
                pages.append(ScrapedPage(
                    url=url, title=title, depth=depth, content=content,
                    scraped_at=datetime.now(timezone.utc).isoformat()
                ))
                logger.info(f"[{len(pages)}/{site.max_pages}] depth={depth} Scraped: {url}")

            if depth < site.max_depth:
                for a in soup.find_all("a", href=True):
                    normalized = _normalize_url(url, a["href"])
                    if normalized and normalized not in visited:
                        queue.append((normalized, depth + 1))

            await asyncio.sleep(site.politeness_delay)

    return pages